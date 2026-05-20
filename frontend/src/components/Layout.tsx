import { Outlet } from "react-router-dom";
import { Header } from "./Header";

export function Layout() {
  return (
    <div className="flex min-h-full flex-col">
      <Header />
      <main className="flex-1">
        <div className="mx-auto w-full max-w-6xl px-4 py-6 md:px-6 md:py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
