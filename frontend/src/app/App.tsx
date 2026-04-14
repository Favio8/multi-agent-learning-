import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";

const DashboardPage = lazy(() =>
  import("@/pages/dashboard-page").then((module) => ({ default: module.DashboardPage })),
);
const StudyPage = lazy(() =>
  import("@/pages/study-page").then((module) => ({ default: module.StudyPage })),
);
const ReviewPage = lazy(() =>
  import("@/pages/review-page").then((module) => ({ default: module.ReviewPage })),
);
const ReportPage = lazy(() =>
  import("@/pages/report-page").then((module) => ({ default: module.ReportPage })),
);

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route
          path="/"
          element={
            <Suspense fallback={<PageFallback />}>
              <DashboardPage />
            </Suspense>
          }
        />
        <Route
          path="/study"
          element={
            <Suspense fallback={<PageFallback />}>
              <StudyPage />
            </Suspense>
          }
        />
        <Route
          path="/review"
          element={
            <Suspense fallback={<PageFallback />}>
              <ReviewPage />
            </Suspense>
          }
        />
        <Route
          path="/report"
          element={
            <Suspense fallback={<PageFallback />}>
              <ReportPage />
            </Suspense>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function PageFallback() {
  return (
    <div className="glass-panel rounded-[28px] p-8 text-sm text-muted-foreground">
      正在加载页面...
    </div>
  );
}
