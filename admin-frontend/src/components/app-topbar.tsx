import { useLocation, NavLink } from "react-router-dom"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"

export function AppTopbar() {
  const location = useLocation()

  const breadcrumb = location.pathname.split("/").map((node, index, array) => {
    const link = array.slice(0, index + 1).join("/")
    return { node, link }
  }).filter(({ node }) => node)

  return (
    <header className="flex h-16 shrink-0 items-center gap-2 transition-[width,height] ease-linear group-has-[[data-collapsible=icon]]/sidebar-wrapper:h-12">
      <div className="flex items-center gap-2 px-4">
        <SidebarTrigger className="-ml-1" />
        <Separator orientation="vertical" className="mr-2 h-4" />
        <Breadcrumb>
          <BreadcrumbList>
            {breadcrumb.map(({ node, link }, index) => (
              <>
                <BreadcrumbSeparator key={index} />
                <BreadcrumbItem key={`bci-${node}-${index}`}>
                  {
                    (index !== breadcrumb.length - 1 && link) ?
                    <BreadcrumbLink key={`bcl-${node}-${index}`}>
                      <NavLink to={link} className="transition-colors hover:text-foreground">
                        {node}
                      </NavLink>
                    </BreadcrumbLink>
                    :
                    <BreadcrumbPage key={`bcp-${node}-${index}`}>
                      {node}
                    </BreadcrumbPage>
                  }
                </BreadcrumbItem>
              </>
            ))}
          </BreadcrumbList>
        </Breadcrumb>
      </div>
    </header>
  )
}
