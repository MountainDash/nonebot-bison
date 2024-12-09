import { Routes, Route, Navigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { ThemeProvider } from "@/components/theme-provider"
import { Layout } from '@/app/dashboard'
import { Subscriptions } from "@/app/subscriptions"

function App() {

  return (
    <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
      <Layout>
        <Routes>
          <Route path="/statistics" element={<Home />} />
          <Route path="/subscriptions" element={<Subscriptions />} />
          <Route path="/" element={<Navigate to="/subscriptions" />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Layout>
    </ThemeProvider>
  )
}

function Home() {
  return (
    <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
      <div className="grid auto-rows-min gap-4 md:grid-cols-3">
        <div className="aspect-video rounded-xl bg-muted/50" />
        <div className="aspect-video rounded-xl bg-muted/50" />
        <div className="aspect-video rounded-xl bg-muted/50" />
      </div>
      <div className="min-h-[100vh] flex-1 rounded-xl bg-muted/50 md:min-h-min" />
    </div>
  )
}

function NotFound() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-4">
      <div className="flex flex-col items-center justify-center gap-4 border border-secondary w-48 h-32 rounded-md bg-accent">
        <div className="text-4xl text-center">
          错误发生
        </div>
        <Button
          className="bg-background text-secondary-foreground"
          onClick={() => window.history.back()}
        >
          首页
        </Button>
      </div>
    </div>
  )
}

export default App
