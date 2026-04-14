import { Activity, BookOpen, ChevronRight, Gauge, LayoutGrid, Sparkles } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { useAppState } from "@/app/app-state";
import { Input } from "@/components/ui/input";
import { getHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

const navigationItems = [
  { to: "/", label: "概览", icon: LayoutGrid },
  { to: "/study", label: "学习", icon: BookOpen },
  { to: "/review", label: "复习", icon: Sparkles },
  { to: "/report", label: "报告", icon: Gauge },
];

export function AppShell() {
  const location = useLocation();
  const { userId, setUserId } = useAppState();
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    staleTime: 5 * 60_000,
    gcTime: 15 * 60_000,
    retry: 0,
  });

  const routeCopy =
    location.pathname === "/"
      ? { eyebrow: "学习空间", description: "静下来学习，而不是被界面打扰。" }
      : location.pathname === "/study"
        ? { eyebrow: "专注模式", description: "把注意力留给题目，把判断留给自己。" }
        : location.pathname === "/review"
          ? { eyebrow: "复习节奏", description: "今天该复习什么，一眼就能开始。" }
          : { eyebrow: "学习报告", description: "只留下真正有用的进度与反馈。" };

  return (
    <div className="surface-grid min-h-screen">
      <div className="mx-auto flex min-h-screen max-w-[1600px] gap-6 px-4 py-4 sm:px-6 lg:px-8">
        <aside className="glass-panel hidden w-[280px] shrink-0 flex-col rounded-[32px] border border-white/75 px-5 py-6 shadow-shell lg:flex">
          <div className="mb-8 flex items-center gap-3 px-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-[18px] bg-primary/10 text-primary">
              <Activity className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-[-0.02em]">知卡学伴</p>
              <p className="text-xs text-muted-foreground">智能学习工作台</p>
            </div>
          </div>

          <nav className="space-y-2">
            {navigationItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center justify-between rounded-[22px] px-4 py-3 text-sm font-medium transition-all",
                    isActive
                      ? "bg-white/90 text-foreground shadow-sm"
                      : "text-muted-foreground hover:bg-white/65 hover:text-foreground",
                  )
                }
              >
                <span className="flex items-center gap-3">
                  <Icon className="h-4 w-4" />
                  {label}
                </span>
                <ChevronRight className="h-4 w-4 opacity-60" />
              </NavLink>
            ))}
          </nav>

          <div className="mt-auto space-y-4 rounded-[24px] border border-white/70 bg-white/55 p-4 backdrop-blur-xl">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">当前用户</p>
              <Input
                value={userId}
                onChange={(event) => setUserId(event.target.value || "demo_user")}
                placeholder="demo_user"
              />
            </div>
            <div className="flex items-center justify-between rounded-2xl bg-background/70 px-3 py-2 text-xs">
              <span className="text-muted-foreground">API 状态</span>
              <span className={cn("font-medium", health?.status === "healthy" ? "text-success" : "text-warning")}>
                {health?.status === "healthy" ? "已连接" : "检测中"}
              </span>
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col gap-6">
          <header className="glass-panel flex flex-col gap-4 rounded-[30px] border border-white/70 px-5 py-4 shadow-panel sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="eyebrow">{routeCopy.eyebrow}</p>
              <p className="mt-2 text-sm text-muted-foreground">{routeCopy.description}</p>
            </div>
            <div className="nav-chip">{health?.status === "healthy" ? "服务在线" : "正在连接服务"}</div>
          </header>

          <main className="min-h-0 flex-1">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
