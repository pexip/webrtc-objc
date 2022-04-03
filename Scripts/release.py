#!/usr/bin/env vpython3

import os
import sys
import logging
import shutil
import argparse
import requests
import hashlib
from typing import Any, List
from dataclasses import dataclass
from webrtc_workspace import WebRTCWorkspace
from webrtc_builder import WebRTCBuilder

### - CONSTANTS

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_API_URL = 'https://api.github.com/repos/pexip/webrtc-ios-builds'
GITHUB_HEADERS = {
    'accept': 'application/vnd.github.v3+json', 
    'Authorization': f'token {GITHUB_TOKEN}'
}
PLATFORMS = {
    'ios': ['ios', 'simulator'],
    'universal': ['ios', 'simulator', 'mac']
}
BUILD_CONFIGS = [
    {'bitcode': False, 'dsyms': False},
    {'bitcode': False, 'dsyms': True},
    {'bitcode': True, 'dsyms': False}
]

### - CLASSES

@dataclass
class Asset:
    url: str
    checksum: str

@dataclass
class ReleaseDetails:
    webrtc_milestone: str
    webrtc_branch: str
    webrtc_commit: str
    tag: str

    @property
    def name(self) -> str:
        return f"M{self.webrtc_milestone}"

### - FUNCTIONS

def create_assets(workspace: WebRTCWorkspace, upload_url: str) -> str:
    logging.info(f"Creating release assets.")
    assets = []

    for (name, platforms) in list(PLATFORMS.items()):
        for config in BUILD_CONFIGS:
            folder_name = name
            bitcode = config['bitcode']
            dsyms = config['dsyms']
            if bitcode:
                folder_name += '_bitcode'
            if dsyms:
                folder_name += '_dsyms'
            
            builder = WebRTCBuilder(
                workspace.webrtc_path,
                workspace.depot_tools_path,
                os.path.join(workspace.output_path, folder_name),
                bitcode,
                dsyms,
                platforms,
                workspace.version_number
            )
            builder.clean()
            builder.build()
            
            zip_name = f"WebRTC-{folder_name}.zip"
            zip_path = f"{builder.xcframework_path}.zip"
            os.system(f"zip --symlinks -r {zip_path} {builder.xcframework_path}/")
            asset = upload_asset(zip_name, zip_path, upload_url)  
            assets.append(Asset(asset['url'], checksum(zip_path)))
    return assets

def upload_asset(name: str, path: str, url: str) -> Any:
    logging.info(f"Uploading an asset with name {name}.")
    url = url.replace(u'{?name,label}','')
    data = open(path, 'rb')  
    params = {'name': name}
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}', 
        'Content-Length': str(os.stat(path).st_size), 
        'Content-Type': 'application/zip'
    }
    return requests.post(url, params = params, data = data, headers = headers).json()

def checksum(file: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(file, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def update_source_code(asset: Asset):
    logging.info("Updating Package.swift.")
    parent_path = os.path.join(os.getcwd(), os.pardir)
    package_path = os.path.join(parent_path, 'Package.swift')
    os.system(f"sed -i '' 's#url:.*,#url: \"{asset.url}\",#' {package_path}")
    os.system(f"sed -i '' 's#checksum:.*#checksum: \"{asset.checksum}\"#' {package_path}")

def draft_release(details: ReleaseDetails) -> Any:
    logging.info(f"Creating a new draft release {details.tag} on GitHub.")
    body = f"Milestone: {details.name}\n"
    body += f"Branch: {details.webrtc_branch}\n"
    body += f"Commit: {details.webrtc_commit}"
    parameters = { 
        'name': details.name,
        'tag_name': details.tag,
        'draft': True,
        'body': body
    }
    return requests.post(
        f"{GITHUB_API_URL}/releases", 
        json = parameters, 
        headers = GITHUB_HEADERS
    ).json()

def publish_release(id: int, details: ReleaseDetails):
    logging.info(f"Publishing a release {details.tag} on GitHub.")
    os.system('git add .')
    os.system(f"git commit -m \"Update Package.swift for {details.name}\"")
    os.system('git push origin master')
    parameters = {'draft': False}
    requests.patch(
        f"{GITHUB_API_URL}/releases/{id}", 
        json = parameters, 
        headers = GITHUB_HEADERS
    )

def delete_release(release):
    for asset in release['assets']:
        requests.delete(asset['url'], headers = GITHUB_HEADERS)
    requests.delete(release['url'], headers = GITHUB_HEADERS)
    delete_tag(release['tag_name'])

def delete_tag(tag_name: str):
    logging.info(f"Deleting a tag {tag_name} on GitHub.")
    requests.delete(
        f"{GITHUB_API_URL}/git/refs/tags/{tag_name}", 
        headers = GITHUB_HEADERS
    )

## SCRIPT ARGUMENTS

def parse_args() -> List:
    parser = argparse.ArgumentParser(
        description='Release new version of WebRTC xcframework'
    )
    parser.add_argument(
        '--milestone',
        type=str,
        default='stable',
        help='WebRTC milestone. Defaults to latest stable milestone.'
    )
    return parser.parse_args()

### - MAIN

def main():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    args = parse_args()    
    milestone = f"{args.milestone}"
    
    # 1. Prepare workspace
    from webrtc_workspace import WebRTCWorkspace
    workspace = WebRTCWorkspace(milestone)
    workspace.prepare()

    # 2. Create a new release
    release_details = ReleaseDetails(
        workspace.milestone,
        workspace.branch,
        workspace.commit,
        workspace.version_number
    )
    request = requests.get(
        f"{GITHUB_API_URL}/releases/tags/{release_details.tag}", 
        headers = GITHUB_HEADERS
    )
    
    if request.status_code == 200:
        print(f"Release {workspace.version_number} already exists on GitHub. Do you want to delete it?")
        answer = input("yes/no")
        if answer == 'yes' or answer == 'y':
            delete_release(request.json())
        else:
            logging.info(f"Cancelled by user.")
            return 0
    release = draft_release(release_details)

    # 3. Build and upload xcframeworks
    shutil.rmtree(workspace.output_path, ignore_errors = True)
    assets = create_assets(workspace, release['upload_url'])
    
    # 4. Update Package.swift
    update_source_code(asset = assets[-1])

    # 5. Publish a new release
    publish_release(release['id'], release_details)

    # 4. Clean workspace
    workspace.clean()
    
    return 0

if __name__ == '__main__':
  sys.exit(main())