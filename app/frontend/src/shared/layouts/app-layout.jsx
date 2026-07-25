import { useEffect, useState } from "react";
import { Moon, Sun, Wifi, WifiOff } from "lucide-react";
import { SidebarProvider, SidebarTrigger } from "@/shared/ui/sidebar";
import { AppSidebar } from "@/shared/layouts/app-sidebar";
import { Toaster } from "@/shared/ui/sonner";
import { Button } from "@/shared/ui/button";
import { useTheme } from "@/shared/providers/theme";
import { Badge } from "@/shared/ui/badge";
import { cn } from "@/shared/utils/utils";
import { pingBackend } from "@/shared/api/api";

export function AppLayout({ title, subtitle, actions, children }) {
  const { theme, toggle } = useTheme();
  const [backendOnline, setBackendOnline] = useState(null);
  useEffect(() => {
    let active = true;
    async function checkBackend() {
      const ok = await pingBackend();
      if (active) setBackendOnline(ok);
    }
    checkBackend();
    const interval = window.setInterval(checkBackend, 10000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full max-w-[100vw] overflow-x-hidden bg-background">
        <AppSidebar />
        <div className="flex w-full min-w-0 max-w-full flex-1 flex-col overflow-x-hidden">
          <header className="sticky top-0 z-30 flex h-14 w-full max-w-full items-center gap-3 border-b bg-card/80 px-4 backdrop-blur">
            <SidebarTrigger />
            <div className="min-w-0 flex-1 leading-tight">
              <h1 className="truncate text-sm font-semibold text-foreground">{title}</h1>
              {subtitle && (
                <p className="hidden truncate text-xs text-muted-foreground sm:block">{subtitle}</p>
              )}
            </div>
            <div className="ml-auto flex items-center gap-2">
              <Badge
                variant="outline"
                className={cn(
                  "hidden gap-1.5 sm:flex",
                  backendOnline
                    ? "border-success/40 text-success"
                    : "border-destructive/40 text-destructive",
                  backendOnline === null && "border-muted-foreground/40 text-muted-foreground",
                )}
              >
                {backendOnline ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
                {backendOnline === null
                  ? "Verificando señal"
                  : backendOnline
                    ? "Backend local"
                    : "Sin señal"}
              </Badge>
              {actions}
              <Button
                variant="ghost"
                size="icon"
                className="hidden sm:inline-flex"
                onClick={toggle}
                aria-label="Cambiar tema"
              >
                {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
            </div>
          </header>
          <main className="min-w-0 flex-1 overflow-x-hidden p-4 sm:p-6">{children}</main>
        </div>
        <Toaster richColors position="top-right" />
      </div>
    </SidebarProvider>
  );
}
