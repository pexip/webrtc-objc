// swift-tools-version:5.3
import PackageDescription

let package = Package(
    name: "WebRTC",
    platforms: [
    	.iOS(.v13),
        .macOS(.v10_15)
    ],
    products: [
        .library(
            name: "WebRTC",
            targets: ["WebRTC"]
        ),
    ],
    dependencies: [],
    targets: [
        .binaryTarget(
            name: "WebRTC",
            url: "https://api.github.com/repos/pexip/webrtc-ios-builds/releases/assets/64544466.zip",
            checksum: "1ddefa62bfe01fbb2fbebea94c7c7992a26e09d3f0ee6c18ee008f62f498ce6f"
        ),
    ]
)
