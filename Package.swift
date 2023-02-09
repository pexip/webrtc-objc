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
            url: "https://github.com/pexip/webrtc-objc/releases/download/108.0.5359/WebRTC-universal_dsyms.zip",
            checksum: "9178e1a2623c7215c9313fa4e6710a9a209badc8d99cee85f3e732b68c1d9675"
        ),
    ]
)
