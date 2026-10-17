import { CaseWorkspace } from "@/components/case-workspace";
export default async function Page({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  return <CaseWorkspace caseId={(await params).caseId} />;
}
