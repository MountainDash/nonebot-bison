import BisonLogo from "@/assets/bison.png"
import useSWR from "swr";
import { NavLink } from "react-router-dom";
import { api, fetchApi } from "@/api/base"
import { Rss, ChartPie, FileClock } from "lucide-react"
import { SidebarTitle } from "@/components/sidebar-title";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

import { ModeToggle } from "@/components/mode-toggle"

const items = [
  {
    title: "订阅管理",
    url: "/subscriptions",
    icon: Rss,
  },
  {
    title: "运行统计",
    url: "/statistics",
    icon: ChartPie,
  },
  {
    title: "日志查看",
    url: "/logs",
    icon: FileClock,
  },
]

export function AppSidebar() {
  const { data } = useSWR<{
    name: string
    role: string
    bot: string
  }>(api`/api/me`, fetchApi)
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarTitle
          data={{
            logo: BisonLogo,
            name: data?.name || "Unknown",
            role: data?.role || "Error",
            bot: data?.bot || "Bison",
          }}
        />
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>页面</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild tooltip={item.title}>
                    <NavLink to={item.url} className="bg-sidebar text-sidebar-foreground"
                    >
                      <item.icon />
                      <span>{item.title}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <ModeToggle />
      </SidebarFooter>
    </Sidebar>
  )
}
