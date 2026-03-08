import { useEffect, useState } from "react"
import { usePathname } from "next/navigation"

export default function AppBootstrapGuard({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()

  const [isClient, setIsClient] = useState(false)

  // Ensure component runs only on client
  useEffect(() => {
    setIsClient(true)
  }, [])

  console.log("AppBootstrapGuard", {
    pathname,
    isClient,
  })

  // Root path debug
  if (pathname === "/") {
    console.log("ACCESSING ROOT PATH - Should show dashboard")
  }

  // Prevent SSR hydration mismatch
  if (!isClient) {
    return (
      <div className="w-screen h-screen flex items-center justify-center bg-slate-900 text-white">
        Loading StrikeIQ...
      </div>
    )
  }

  return <>{children}</>
}