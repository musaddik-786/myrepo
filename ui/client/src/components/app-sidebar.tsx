import { useState } from "react";
import { Link } from "wouter";
import { LayoutGrid, Pencil, Check, ClipboardList, MessageCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { label: "AI Insights", href: "/", icon: LayoutGrid },
  { label: "Self-service chat", href: "/chat", icon: MessageCircle },
  { label: "Audit trail", href: "/audit", icon: ClipboardList },
];

interface AppSidebarProps {
  activeItem?: string;
}

const ORG_KEY = "sidebar.orgName";
const DEFAULT_ORG = "Jackson Insurance";

function loadOrgName(): string {
  try {
    return localStorage.getItem(ORG_KEY) || DEFAULT_ORG;
  } catch {
    return DEFAULT_ORG;
  }
}

export function AppSidebar({ activeItem = "AI Insights" }: AppSidebarProps) {
  const [orgName, setOrgName] = useState(loadOrgName);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(orgName);

  const startEdit = () => {
    setDraft(orgName);
    setEditing(true);
  };
  const save = () => {
    const next = draft.trim() || DEFAULT_ORG;
    setOrgName(next);
    setEditing(false);
    try {
      localStorage.setItem(ORG_KEY, next);
    } catch {
      /* storage unavailable: keep the name for this session only */
    }
  };

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col bg-sidebar text-sidebar-foreground border-r border-sidebar-border">
      <p className="px-5 pb-2 pt-5 text-[11px] font-semibold uppercase tracking-wider text-sidebar-foreground/50">Customer</p>

      <div className="px-4 mb-4">
        <div className="flex items-center justify-between rounded-md border border-sidebar-border bg-white/5 px-3 py-2 text-sm">
          {editing ? (
            <input
              autoFocus
              value={draft}
              maxLength={40}
              aria-label="Organization name"
              onChange={(e) => setDraft(e.target.value)}
              onBlur={save}
              onKeyDown={(e) => {
                if (e.key === "Enter") save();
                if (e.key === "Escape") setEditing(false);
              }}
              className="min-w-0 flex-1 bg-transparent outline-none"
            />
          ) : (
            <span className="truncate">{orgName}</span>
          )}
          <button
            type="button"
            aria-label={editing ? "Save name" : "Edit name"}
            onMouseDown={(e) => e.preventDefault()}
            onClick={editing ? save : startEdit}
            className="ml-2 shrink-0 rounded p-0.5 text-sidebar-foreground/50 hover:text-sidebar-foreground"
          >
            {editing ? <Check className="h-3.5 w-3.5" /> : <Pencil className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      <div className="px-5 py-2">
        <span className="text-xs font-semibold tracking-wider text-sidebar-foreground/40">
          WORKSPACE
        </span>
      </div>

      <nav className="flex-1 px-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = item.label === activeItem;
          return (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                "flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-sidebar-foreground/80 hover:bg-white/5 hover:text-sidebar-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
