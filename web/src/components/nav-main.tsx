"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

export function NavMain({
  items,
  label,
}: {
  label?: string
  items: {
    title: string
    // Optional second line (deployed-terminal alignment: descriptive
    // subtitle under the nav title, e.g. "机构目录 · 全部机构").
    sub?: string
    url: string
    icon: React.ReactNode
  }[]
}) {
  const pathname = usePathname()

  return (
    <SidebarGroup>
      {label && <SidebarGroupLabel>{label}</SidebarGroupLabel>}
      <SidebarMenu>
        {items.map((item) => (
          <SidebarMenuItem key={item.title}>
            <SidebarMenuButton
              isActive={pathname === item.url}
              tooltip={item.title}
              render={<Link href={item.url} />}
            >
              {item.icon}
              <span className="flex min-w-0 flex-col">
                <span className="truncate">{item.title}</span>
                {item.sub ? (
                  <span className="truncate text-[10px] leading-tight text-muted-foreground">
                    {item.sub}
                  </span>
                ) : null}
              </span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        ))}
      </SidebarMenu>
    </SidebarGroup>
  )
}
