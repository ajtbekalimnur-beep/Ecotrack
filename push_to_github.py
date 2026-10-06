"""
EcoTrack - Automatic GitHub Push
Automatically authenticates and pushes to GitHub using Device Flow.
"""
import json
import time
import webbrowser
import subprocess
import sys
import os

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

GIT_EXE = r"C:\Users\Admin\AppData\Local\GitHubDesktop\app-3.6.6\resources\app\git\cmd\git.exe"
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
# GitHub CLI's official OAuth App client_id (public, safe to use)
CLIENT_ID = "178c6fc778ccc68e1d6a"

def run_git(*args):
    result = subprocess.run(
        [GIT_EXE] + list(args), 
        cwd=REPO_DIR, capture_output=True, text=True
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def device_flow_auth():
    """GitHub Device Flow - user just clicks authorize in browser"""
    print("\n[1/3] Requesting device code from GitHub...")
    
    resp = requests.post(
        "https://github.com/login/device/code",
        data={"client_id": CLIENT_ID, "scope": "repo"},
        headers={"Accept": "application/json"}
    )
    data = resp.json()
    
    device_code = data["device_code"]
    user_code = data["user_code"]
    verification_uri = data["verification_uri"]
    interval = data.get("interval", 5)
    expires_in = data.get("expires_in", 900)
    
    print(f"\n{'='*60}")
    print(f"  OPENING BROWSER...")
    print(f"  If asked, enter this code: {user_code}")
    print(f"{'='*60}")
    print(f"\n  Then click 'Authorize' - that's it!\n")
    
    # Auto-open browser with the verification URI
    webbrowser.open(verification_uri)
    
    # Also copy code to clipboard if possible
    try:
        subprocess.run(
            ["clip"], input=user_code.encode(), check=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        print(f"  Code '{user_code}' copied to clipboard! Just paste it.\n")
    except:
        pass
    
    print("[2/3] Waiting for you to authorize in browser...")
    
    start = time.time()
    while time.time() - start < expires_in:
        time.sleep(interval + 1)
        
        resp = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
            },
            headers={"Accept": "application/json"}
        )
        result = resp.json()
        
        if "access_token" in result:
            print("  Authorization successful!")
            return result["access_token"]
        
        error = result.get("error", "")
        if error == "authorization_pending":
            sys.stdout.write(".")
            sys.stdout.flush()
            continue
        elif error == "slow_down":
            interval = result.get("interval", interval + 5)
            continue
        elif error == "expired_token":
            print("\n  Code expired. Please run the script again.")
            return None
        elif error == "access_denied":
            print("\n  Access denied by user.")
            return None
    
    print("\n  Timeout waiting for authorization.")
    return None

def push_to_github(token):
    """Push using the obtained token"""
    print("\n[3/3] Pushing to GitHub...")
    
    # Get username
    resp = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"token {token}"}
    )
    user_data = resp.json()
    username = user_data.get("login", "ajtbekalimnur-beep")
    print(f"  Logged in as: {username}")
    
    # Check if repo exists, if not create it
    repo_name = "Ecotrack"
    resp = requests.get(
        f"https://api.github.com/repos/{username}/{repo_name}",
        headers={"Authorization": f"token {token}"}
    )
    
    if resp.status_code == 404:
        print(f"  Creating repository '{repo_name}'...")
        resp = requests.post(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"token {token}"},
            json={
                "name": repo_name,
                "description": "EcoTrack - Smart City Environmental Monitoring Platform",
                "private": False
            }
        )
        if resp.status_code in (201, 200):
            print(f"  Repository created!")
        else:
            print(f"  Repo response: {resp.status_code} {resp.text[:200]}")
    else:
        print(f"  Repository '{repo_name}' exists.")
    
    # Set remote with token and push
    remote_url = f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
    run_git("remote", "set-url", "origin", remote_url)
    
    # Commit any uncommitted changes
    run_git("add", ".")
    run_git("commit", "-m", "Update EcoTrack - local server and push scripts")
    
    out, err, code = run_git("push", "origin", "main")
    
    # Also push to gh-pages for free global web hosting
    print("  Publishing to GitHub Pages (gh-pages)...")
    run_git("push", "origin", "main:gh-pages", "--force")
    
    # Clean token from URL immediately
    run_git("remote", "set-url", "origin", f"https://github.com/{username}/{repo_name}.git")
    
    # Save token for future git operations
    run_git("config", "--global", "credential.helper", "store")
    
    if code == 0:
        print(f"\n{'='*60}")
        print(f"  SUCCESS! Project pushed to GitHub!")
        print(f"  https://github.com/{username}/{repo_name}")
        print(f"{'='*60}")
        return True
    else:
        if "rejected" in err or "non-fast-forward" in err:
            print("  Trying force push...")
            run_git("remote", "set-url", "origin", remote_url)
            out, err, code = run_git("push", "origin", "main", "--force")
            run_git("remote", "set-url", "origin", f"https://github.com/{username}/{repo_name}.git")
            if code == 0:
                print(f"\n  SUCCESS! Force pushed to GitHub!")
                print(f"  https://github.com/{username}/{repo_name}")
                return True
        
        print(f"\n  Push failed: {err}")
        return False

def main():
    print("=" * 60)
    print("  EcoTrack - Automatic GitHub Push")
    print("=" * 60)
    
    # Check for saved token
    token_file = os.path.join(REPO_DIR, ".github_token")
    token = None
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            token = f.read().strip()
        # Verify token
        resp = requests.get("https://api.github.com/user", headers={"Authorization": f"token {token}"})
        if resp.status_code != 200:
            token = None

    if not token:
        token = device_flow_auth()
        if token:
            with open(token_file, "w") as f:
                f.write(token)
    
    if not token:
        print("\nFailed to get token. Exiting.")
        input("Press Enter to close...")
        return
    
    # Push
    success = push_to_github(token)
    
    if not success:
        print("\nPush failed. Please check errors above.")
    
    input("\nPress Enter to close...")

if __name__ == "__main__":
    main()
