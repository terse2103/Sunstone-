import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <section className="rounded-xl border border-ink-200 bg-white p-6 text-center md:p-10">
      <p className="text-sm font-semibold uppercase tracking-wide text-brand-600">404</p>
      <h1 className="mt-2 text-2xl font-semibold text-ink-900 md:text-3xl">
        Page not found
      </h1>
      <p className="mt-2 text-ink-600">
        That route isn’t part of PlacementIQ.
      </p>
      <Link
        to="/"
        className="mt-6 inline-flex rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
      >
        Back to login
      </Link>
    </section>
  );
}
