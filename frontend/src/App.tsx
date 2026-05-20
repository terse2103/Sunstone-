import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { RequireAuth } from "./components/RequireAuth";
import CounselorDashboard from "./pages/CounselorDashboard";
import EvalsPage from "./pages/EvalsPage";
import InterventionDetail from "./pages/InterventionDetail";
import LoginPage from "./pages/LoginPage";
import NotFound from "./pages/NotFound";
import StudentDashboard from "./pages/StudentDashboard";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<LoginPage />} />
        <Route
          path="student/:id"
          element={
            <RequireAuth>
              <StudentDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="counselor"
          element={
            <RequireAuth roles={["counselor"]}>
              <CounselorDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="counselor/student/:id"
          element={
            <RequireAuth roles={["counselor"]}>
              <InterventionDetail />
            </RequireAuth>
          }
        />
        <Route path="evals" element={<EvalsPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
