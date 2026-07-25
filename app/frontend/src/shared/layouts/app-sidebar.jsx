import { Link, useLocation } from "react-router-dom";
import { Boxes, ClipboardList, Printer, Settings, History } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/shared/ui/sidebar";

const nav = [
  { title: "Imprimir etiquetas", url: "/", icon: Printer },
  { title: "Imprimir de inventario", url: "/inventory-print", icon: Boxes },
  { title: "Imprimir por entrada", url: "/inventory-entry-print", icon: ClipboardList },
  { title: "Configuraciones", url: "/settings", icon: Settings },
  { title: "Historial de impresión", url: "/history", icon: History },
];

export function AppSidebar() {
  const { pathname } = useLocation();
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-3 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground transition-[width,height] group-data-[collapsible=icon]:size-8">
            <Printer className="size-5 transition-[width,height] group-data-[collapsible=icon]:size-4" />
          </div>
          <div className="flex flex-col leading-tight group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-semibold">StockLabel</span>
            <span className="text-xs text-muted-foreground">
              Software para impresión de etiquetas
            </span>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Operación</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {nav.map((item) => {
                const active = pathname === item.url;
                return (
                  <SidebarMenuItem key={item.url}>
                    <SidebarMenuButton asChild isActive={active} tooltip={item.title}>
                      <Link to={item.url} className="flex items-center gap-2">
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
