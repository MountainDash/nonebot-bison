import { BotMessageSquare } from "lucide-react";
import { Avatar, AvatarImage } from "@/components/ui/avatar";
import { SidebarMenu, SidebarMenuButton } from "@/components/ui/sidebar";

export function SidebarTitle({
  data,
}: {
  data: {
    logo: string;
    name: string;
    role: string;
    bot: string;
  };
}) {
  const ROLE_MAP: Record<string, string> = {
    "superuser": "超级用户",
    "groupadmin": "群管理员",
    "singleuser": "个人订阅",
  }

  return (
    <SidebarMenu>
      <SidebarMenuButton
        size="lg"
        className="bg-sidebar-accent text-sidebar-accent-foreground"
        tooltip={data.name}
      >
        <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
          <Avatar className="size-7">
            <AvatarImage src={data.logo} alt="bison logo" />
          </Avatar>
        </div>
        <div className="grid flex-1 text-left text-sm leading-tight">
          <span className="truncate font-semibold">
            {data.name}
          </span>
          <div className="flex items-center text-sidebar-accent-foreground">
            <BotMessageSquare className="size-3" />
            <span className="ml-1 truncate text-xs font-extralight">{data.bot}</span>
          </div>
        </div>
        <div className="flex items-center justify-center w-16 h-5 bg-sidebar-primary rounded-lg">
          <span className="text-xs text-sidebar-primary-foreground truncate"
          >{
            ROLE_MAP[data.role] || "未知角色"
          }</span>
        </div>
      </SidebarMenuButton>
    </SidebarMenu>
  )
}
