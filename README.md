# WebRTC binaries for Apple platforms

## Installation

### Swift Package Manager

**For universal `xcframework` and w/ dsyms:**

```swift
dependencies: [
    .Package(url: "https://github.com/pexip/webrtc-objc", .upToNextMajor("100.0.0"))
]
```

**For any other `xcframework` provided by this repo (iOS only, w/ dsyms, etc):**

- Create a local Swift Package and use [Package.swift](https://github.com/pexip/webrtc-objc/blob/master/Package.swift) as a template
- Url and checksum of the binary can be found in the "Binaries" section of the release description

### Manual

- Download one of the archives from the GitHub release
- Unzip the file and add the xcframework to your Xcode project

## Create a new release

1. Install [direnv](https://direnv.net)
```console
$ brew install direnv
```
2. Create `.envrc` file with your GitHub token
```
export GITHUB_TOKEN=token
```
3. Run python3 script
```console
$ cd Scripts
$ python release.py
```

**Running the script will:**
- Build latest stable version of WebRTC framework for iOS and macOS 
- Create a new release on GitHub
- Upload xcframeworks as release assets:
  - iOS (device, simulator):
    - "WebRTC-ios.zip" - w/o dsyms
    - "WebRTC-ios_dsyms.zip" - w/ dsyms
  - Universal (iOS device, iOS simulator, macOS):
    - "WebRTC-universal.zip" - w/o dsyms
    - "WebRTC-universal_dsyms.zip" - w/ dsyms
- Update url of the binary target in `Package.swift` with new asset url (universal w/ dsyms)

## Build

- Build latest stable version of WebRTC framework locally:

```console
$ cd Scripts
$ python build.py
```

- Build WebRTC with custom arguments:

```console
$ cd Scripts
$ python build.py --milestone 100 --platforms ios simulator mac catalyst --dsyms
```
