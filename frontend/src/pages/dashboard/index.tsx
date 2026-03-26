import dynamic from 'next/dynamic';

const Dashboard = dynamic(() => import('@/components/Dashboard'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <div className="text-gray-400">Loading Dashboard...</div>
      </div>
    </div>
  ),
});

export default function DashboardPage() {
  // Safe fallback UI for missing environment variables
  if (!process.env.NEXT_PUBLIC_API_URL) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-red-500 text-xl font-bold mb-4">Configuration Error</div>
          <div className="text-gray-300">API URL missing</div>
        </div>
      </div>
    );
  }

  return <Dashboard initialSymbol="NIFTY" />;
}
