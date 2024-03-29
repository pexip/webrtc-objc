#!/usr/bin/env vpython3

# Copyright 2022-2023 Pexip AS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import logging
import shutil
import argparse
import requests
import subprocess
import hashlib
from typing import Any, List
from dataclasses import dataclass
from webrtc_workspace import WebRTCWorkspace
from webrtc_builder import WebRTCBuilder
from webrtc_builder import XCFRAMEWORK_NAME

### - CONSTANTS

CWD_PATH = os.path.dirname(os.path.realpath(__file__))
ROOT_PATH = os.path.join(CWD_PATH, os.pardir)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_URL = 'https://github.com/pexip/webrtc-objc'
GITHUB_API_URL = 'https://api.github.com/repos/pexip/webrtc-objc'
GITHUB_HEADERS = {
    'accept': 'application/vnd.github.v3+json', 
    'Authorization': f'token {GITHUB_TOKEN}'
}
PLATFORMS = {
    'ios': ['ios', 'simulator'],
    'universal': ['ios', 'simulator', 'mac']
}
BUILD_CONFIGS = [
    {'dsyms': False},
    {'dsyms': True}
]

### - CLASSES

@dataclass
class Asset:
    name: str
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
    
    def asset_url(self, asset: Asset) -> str:
        return f"{GITHUB_URL}/releases/download/{self.tag}/{asset.name}"

### - FUNCTIONS

def create_assets(workspace: WebRTCWorkspace, upload_url: str) -> str:
    logging.info(f"Creating release assets.")
    assets = []

    for (name, platforms) in list(PLATFORMS.items()):
        for config in BUILD_CONFIGS:
            folder_name = name
            dsyms = config['dsyms']
            if dsyms:
                folder_name += '_dsyms'
            
            builder = WebRTCBuilder(
                workspace.webrtc_path,
                workspace.depot_tools_path,
                os.path.join(workspace.output_path, folder_name),
                dsyms,
                platforms,
                workspace.version_number
            )
            builder.clean()
            builder.build()
            
            zip_name = f"WebRTC-{folder_name}.zip"
            zip_path = os.path.join(builder.output_path, zip_name)
            subprocess.check_call(
                ['zip', '--symlinks', '-r', zip_name, f"{XCFRAMEWORK_NAME}/"], 
                cwd=builder.output_path
            )
            asset = upload_asset(zip_name, zip_path, upload_url)  
            assets.append(Asset(zip_name, checksum(zip_path)))
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

def update_source_code(asset: Asset, details: ReleaseDetails):
    logging.info("Updating Package.swift and Podspec")
    package_path = os.path.join(ROOT_PATH, 'Package.swift')
    os.system(f"sed -i '' 's#url:.*,#url: \"{details.asset_url(asset)}\",#' {package_path}")
    os.system(f"sed -i '' 's#checksum:.*#checksum: \"{asset.checksum}\"#' {package_path}")
    podspec_path = os.path.join(ROOT_PATH, 'WebRTCObjc.podspec')
    os.system(f"sed -i '' 's#http:.*,#http: \"{details.asset_url(asset)}\",#' {podspec_path}")
    os.system(f"sed -i '' 's#sha256:.*,#sha256: \"{asset.checksum}\",#' {podspec_path}")

def draft_release(details: ReleaseDetails) -> Any:
    logging.info(f"Creating a new draft release {details.tag} on GitHub.")
    parameters = { 
        'name': details.name,
        'tag_name': details.tag,
        'draft': True,
        'body': ""
    }
    return requests.post(
        f"{GITHUB_API_URL}/releases", 
        json = parameters, 
        headers = GITHUB_HEADERS
    ).json()

def publish_release(id: int, details: ReleaseDetails, assets: List[Asset]):
    logging.info(f"Publishing a release {details.tag} on GitHub.")
    commit_message = f"\"Release {details.name}\""
    subprocess.check_call(['git', 'add', '.'], cwd=ROOT_PATH)
    subprocess.check_call(['git', 'commit', '-m', commit_message], cwd=ROOT_PATH)
    subprocess.check_call(['git', 'push', 'origin', 'main'], cwd=ROOT_PATH)
    
    body = f"**Milestone**: {details.name}\n"
    body += f"**Branch**: {details.webrtc_branch}\n"
    body += f"**Commit**: {details.webrtc_commit}\n\n"
    body += "**Binaries**:\n\n"
    
    for asset in assets:
        body += f"Name: {asset.name}\n"
        body += f"URL: {details.asset_url(asset)}\n"
        body += f"Checksum: {asset.checksum}\n\n"    
    
    parameters = {'draft': False, 'body': body}
    
    requests.patch(
        f"{GITHUB_API_URL}/releases/{id}", 
        json = parameters, 
        headers = GITHUB_HEADERS
    )

def delete_release(release: Any):
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

### - SCRIPT ARGUMENTS

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
    workspace.clean()
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
    update_source_code(asset = assets[-1], details=release_details)

    # 5. Publish a new release
    publish_release(release['id'], release_details, assets)

    # 4. Clean workspace
    workspace.clean()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
