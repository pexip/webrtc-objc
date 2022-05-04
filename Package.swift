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
            url: "https://api.github.com/repos/pexip/webrtc-ios-builds/releases/assets/61528824.zip",
            checksum: "ebfcf41e5171fa2c34cf06b6378f499fa41cf96435b4d32446d8cab73fff700a"
        ),
    ]
)
