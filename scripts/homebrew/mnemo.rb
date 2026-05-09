# Homebrew formula for Mnemo
# Place this in a tap repo: mnemo-ai/homebrew-tap/Formula/mnemo.rb
# Users install with: brew install mnemo-ai/tap/mnemo

class Mnemo < Formula
  desc "Persistent memory and code intelligence for AI coding assistants"
  homepage "https://github.com/nikhil1057/Mnemo"
  version "0.1.0"

  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/nikhil1057/Mnemo/releases/download/v#{version}/mnemo-darwin-arm64"
      sha256 "PLACEHOLDER_SHA256"
    else
      url "https://github.com/nikhil1057/Mnemo/releases/download/v#{version}/mnemo-darwin-x64"
      sha256 "PLACEHOLDER_SHA256"
    end
  end

  on_linux do
    url "https://github.com/nikhil1057/Mnemo/releases/download/v#{version}/mnemo-linux-x64"
    sha256 "PLACEHOLDER_SHA256"
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
