import { Moon, Sun } from "lucide-react"

import { Button } from "@/components/ui/button"

import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"

import { useTheme } from "@/components/theme-provider"
import type { Theme } from "@/components/theme-provider"


export function ModeToggle() {
  const { theme, setTheme } = useTheme()
  const themeList: Theme[] = ["light", "dark"]

  const toggleTheme = () => {
    const currentTheme = themeList.indexOf(theme)
    const nextTheme = themeList[(currentTheme + 1) % themeList.length]
    setTheme(nextTheme)
  }

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>
        <Button variant="outline" size="icon" onClick={toggleTheme}>
          <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Toggle theme</span>
        </Button>
      </ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem onClick={() => setTheme("light")}>
          Light
        </ContextMenuItem>
        <ContextMenuItem onClick={() => setTheme("dark")}>
          Dark
        </ContextMenuItem>
        <ContextMenuItem onClick={() => setTheme("system")}>
          System
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  )
}
