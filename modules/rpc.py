import httpx
import xml.etree.ElementTree as ET


def build_value(parent, value):
    value_node = ET.SubElement(parent, "value")

    if isinstance(value, bool):
        boolean_node = ET.SubElement(value_node, "boolean")
        boolean_node.text = "1" if value else "0"

    elif isinstance(value, int):
        int_node = ET.SubElement(value_node, "int")
        int_node.text = str(value)

    elif isinstance(value, list):
        array_node = ET.SubElement(value_node, "array")
        data_node = ET.SubElement(array_node, "data")

        for item in value:
            build_value(data_node, item)

    elif isinstance(value, dict):
        struct_node = ET.SubElement(value_node, "struct")

        for key, item in value.items():
            member_node = ET.SubElement(struct_node, "member")

            name_node = ET.SubElement(member_node, "name")
            name_node.text = str(key)

            build_value(member_node, item)

    else:
        string_node = ET.SubElement(value_node, "string")
        string_node.text = str(value)


def build_payload(method, params=None):
    root = ET.Element("methodCall")

    method_name = ET.SubElement(root, "methodName")
    method_name.text = method

    if params:
        params_node = ET.SubElement(root, "params")

        for param in params:
            param_node = ET.SubElement(params_node, "param")
            build_value(param_node, param)

    return ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True
    )


def call(url, method, params=None):

    payload = build_payload(method, params)

    response = httpx.post(
        url,
        content=payload,
        headers={
            "Content-Type": "text/xml"
        },
        timeout=10
    )

    return response


def parse_response(response):
    try:
        root = ET.fromstring(response.text)
    except ET.ParseError:
        return None

    if root.tag != "methodResponse":
        return None

    if root.find("fault") is not None:
        return {
            "type": "fault",
            "root": root
        }

    return {
        "type": "success",
        "root": root
    }


def parse_methods(root):
    methods = []

    for element in root.iter("string"):
        if element.text:
            methods.append(element.text)

    return methods


def parse_capabilities(root):
    capabilities = []

    for member in root.iter("member"):
        name = member.find("name")

        if name is None or not name.text:
            continue

        capability_name = name.text

        if capability_name in (
            "specUrl",
            "specVersion"
        ):
            continue

        capabilities.append(capability_name)

    return capabilities


def parse_fault(root):
    fault = {}

    fault_node = root.find("fault")

    if fault_node is None:
        return fault

    struct = fault_node.find(".//struct")

    if struct is None:
        return fault

    for member in struct.findall("member"):
        name = member.find("name")
        value = member.find("value")

        if name is None or value is None:
            continue

        fault[name.text] = "".join(value.itertext()).strip()

    return fault


def parse_struct_array(root):
    entries = []

    array = root.find(".//array/data")

    if array is None:
        return entries

    for value in array.findall("value"):
        struct = value.find("struct")

        if struct is None:
            continue

        entry = {}

        for member in struct.findall("member"):
            name = member.find("name")
            value_node = member.find("value")

            if name is None or value_node is None:
                continue

            entry[name.text] = "".join(value_node.itertext()).strip()

        entries.append(entry)

    return entries