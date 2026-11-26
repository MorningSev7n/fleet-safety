"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const icon = (d: React.ReactNode) => (
  <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{d}</svg>
);

const LINKS = [
  { href: "/", label: "Overview", short: "Overview", icon: icon(<><rect x="3" y="3" width="7" height="9" rx="1" /><rect x="14" y="3" width="7" height="5" rx="1" /><rect x="14" y="12" width="7" height="9" rx="1" /><rect x="3" y="16" width="7" height="5" rx="1" /></>) },
  { href: "/live", label: "Live monitor", short: "Live", live: true, icon: icon(<><path d="M23 7l-7 5 7 5V7z" /><rect x="1" y="5" width="15" height="14" rx="2" /></>) },
  { href: "/drivers", label: "Drivers", short: "Drivers", icon: icon(<><circle cx="9" cy="7" r="4" /><path d="M1 21v-2a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v2" /><path d="M17 3.1a4 4 0 0 1 0 7.8M23 21v-2a4 4 0 0 0-3-3.9" /></>) },
  { href: "/driving", label: "Driving behaviour", short: "Driving", icon: icon(<><circle cx="12" cy="12" r="9" /><path d="M12 12l4-4" /><path d="M12 3v2M3 12h2M19 12h2" /></>) },
  { href: "/reports", label: "Reports", short: "Reports", icon: icon(<><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M8 13h8M8 17h5" /></>) },
];

export default function Nav() {
  const path = usePathname();
  return (
    <nav aria-label="Main" className="sidebar">
      <div className="brand">
        <span className="brand-mark">
          <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0B0E13" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z" /></svg>
        </span>
        Fleet Safety
      </div>
      {LINKS.map((l) => (
        <Link key={l.href} href={l.href} className="nav-link" aria-current={path === l.href ? "page" : undefined}>
          {l.icon}
          <span className="nav-long">{l.label}</span>
          <span className="nav-short">{l.short}</span>
          {l.live && <span className="nav-dot" aria-hidden="true" />}
        </Link>
      ))}
    </nav>
  );
}
