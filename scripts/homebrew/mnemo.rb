# Homebrew formula for Mnemo
# Place this in a tap repo: mnemo-ai/homebrew-tap/Formula/mnemo.rb
# Users install with: brew install mnemo-ai/tap/mnemo

class Mnemo < Formula
  desc "Persistent memory and code intelligence for AI coding assistants"
  homepage "https://github.com/nikhil1057/Mnemo"
  version "0.1.0"

  on_macos do
    url "https://github.com/nikhil1057/Mnemo/releases/download/v#{version}/mnemo-darwin-arm64"
    sha256 "d747a3491c3109f1a15ead4d3dd9f4a8af68d4a9d19f2ac693fdaad88c92c94b"
  end

  on_linux do
    url "https://github.com/nikhil1057/Mnemo/releases/download/v#{version}/mnemo-linux-x64"
    sha256 "ff8793fdcc86d26c4bd8fb15576ce0dfe3b535bc84aea61a3d763dd5f0ee0395"
  end

  def install
    binary = Dir["mnemo-*"].first || "mnemo"
    bin.install binary => "mnemo"
  end

  def post_install
    bin.install_symlink bin/"mnemo" => "mnemo-mcp"
  end

  test do
    assert_match "Usage", shell_output("#{bin}/mnemo --help")
  end
end
