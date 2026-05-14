export default function Footer() {
  return (
    <footer className="border-t border-border-subtle py-10 px-6">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <img src="/Mnemo/icon.png" alt="Mnemo" className="w-5 h-5 rounded" />
          <span className="text-sm font-semibold text-white">Mnemo</span>
          <span className="text-xs text-gray-600 font-mono">v0.4.0</span>
        </div>
        <div className="flex items-center gap-6">
          <a href="https://pypi.org/project/mnemo-dev/" className="text-xs text-gray-500 hover:text-accent transition-colors">PyPI</a>
          <a href="https://www.npmjs.com/package/@mnemo-dev/mcp" className="text-xs text-gray-500 hover:text-accent transition-colors">npm</a>
          <a href="https://github.com/Mnemo-mcp/Mnemo" className="text-xs text-gray-500 hover:text-accent transition-colors">GitHub</a>
          <a href="https://marketplace.visualstudio.com/items?itemName=Nikhil1057.mnemo-vscode" className="text-xs text-gray-500 hover:text-accent transition-colors">VS Code</a>
        </div>
        <p className="text-xs text-gray-600">AGPL-3.0</p>
      </div>
    </footer>
  );
}
