import { useEffect, useState } from "react";
import { CircleCheck, LoaderCircle, Moon, Printer, Sun, WifiOff } from "lucide-react";
import { SidebarProvider, SidebarTrigger } from "@/shared/ui/sidebar";
import { AppSidebar } from "@/shared/layouts/app-sidebar";
import { Toaster } from "@/shared/ui/sonner";
import { Button } from "@/shared/ui/button";
import { useTheme } from "@/shared/providers/theme";
import { Badge } from "@/shared/ui/badge";
import { cn } from "@/shared/utils/utils";
import { getPrinterStatus, pingBackend } from "@/shared/api/api";

export function AppLayout({ title, subtitle, actions, children }) {
  const { theme, toggle } = useTheme();
  const [backendOnline, setBackendOnline] = useState(null);
  const [agentStatus, setAgentStatus] = useState(null);
  useEffect(() => {
    let active = true;
    async function checkSystem() {
      const ok = await pingBackend();
      if (!active) return;
      setBackendOnline(ok);
      if (!ok) {
        setAgentStatus(null);
        return;
      }
      try {
        const status = await getPrinterStatus();
        if (active) setAgentStatus(status);
      } catch {
        if (active) setAgentStatus({ online: false, printer_ok: false });
      }
    }
    checkSystem();
    const interval = window.setInterval(checkSystem, 10000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  const systemStatus =
    backendOnline === null
      ? {
          label: "Verificando sistema",
          icon: LoaderCircle,
          className: "border-warning/50 text-warning",
        }
      : !backendOnline
        ? {
            label: "Servidor sin conexión",
            icon: WifiOff,
            className: "border-destructive/40 text-destructive",
          }
        : agentStatus === null
          ? {
              label: "Verificando sistema",
              icon: LoaderCircle,
              className: "border-warning/50 text-warning",
            }
        : !agentStatus?.online
          ? {
              label: "Agente desconectado",
              icon: WifiOff,
              className: "border-destructive/40 text-destructive",
            }
          : !agentStatus.printer_ok
            ? {
                label: "Impresora offline",
                icon: Printer,
                className: "border-destructive/40 text-destructive",
              }
            : {
                label: "Listo para imprimir",
                icon: CircleCheck,
                className: "border-success/40 text-success",
              };
  const SystemStatusIcon = systemStatus.icon;
  return (
    <SidebarProvider>
      <div className="flex h-dvh w-full max-w-[100vw] overflow-hidden bg-background">
        <AppSidebar />
        <div className="flex h-dvh w-full min-w-0 max-w-full flex-1 flex-col overflow-x-hidden overflow-y-auto">
          <header className="sticky top-0 z-30 flex h-14 w-full max-w-full shrink-0 items-center gap-3 border-b bg-card/80 px-4 backdrop-blur">
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
                className={cn("hidden gap-1.5 sm:flex", systemStatus.className)}
                title={agentStatus?.message || systemStatus.label}
              >
                <SystemStatusIcon
                  className={cn(
                    "h-3 w-3",
                    systemStatus.label === "Verificando sistema" && "animate-spin",
                  )}
                />
                {systemStatus.label}
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
