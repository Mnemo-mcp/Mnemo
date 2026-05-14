export default function Footer() {
  return (
    <footer className="border-t border-white/[0.06] py-10 px-6">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-accent-pink flex items-center justify-center font-bold text-[10px] text-white">
            M
          </div>
          <span className="font-semibold text-sm">Mnemo</span>
        </div>
        <div className="flex items-center gap-6 text-xs text-gray-500">
          <a href="https://github.com/Mnemo-mcp/Mnemo" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">
            GitHub
          </a>
          <a href="https://github.com/Mnemo-mcp/Mnemo/issues" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">
            Issues
          </a>
          <a href="https://github.com/Mnemo-mcp/Mnemo/releases" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">
            Releases
          </a>
        </div>
        <span className="text-[10px] text-gray-600 uppercase tracking-wider">AGPL-3.0</span>
      </div>
    </footer>
  );
}
