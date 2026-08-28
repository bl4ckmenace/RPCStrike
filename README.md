# RPCStrike

**DISCLAIMER:**<br>
This tool was built to test WordPress websites for XML-RPC vulnerabilities for authorized security testing only.<br>
Only run it against targets you own or have explicit permission to test.<br>
Unauthorized use may violate computer fraud laws in your jurisdiction.<br>

## Features
### 1. WordPress user enumeration:
Checks REST API for WordPress usernames.
### 2. WordPress login:
Logs in via wp.getUsersBlogs or blogger.getUsersBlogs to confirm successful login.
### 3. Brute-force amplification:
Uses multicall to send several username/password entries in one request.
### 4. Pingback test:
A basic test that sends pingback.ping with a source and target URL and reports whether it was accepted or rejected.
There’s also an optional out-of-band verification mode using Interactsh. That mode matters if you’re trying to actually
demonstrate SSRF.<br>

## Requirements
Python 3.9 or newer<br>
httpx (installed via requirements.txt)<br>
[Interactsh-client](https://github.com/projectdiscovery/interactsh) (Optional)

### Installation and Usage

```
git clone https://github.com/bl4ckmenace/RPCStrike
cd RPCStrike
pip install -r requirements.txt
python main.py https://wordpress-website.com/
```
<br>

**This tool is still under development and will be improved over time.**
