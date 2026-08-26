"use client";

import { useEffect, useState } from "react";

import { AuditDashboard } from "@/components/audit-dashboard";
import { DemoPicker } from "@/components/demo-picker";
import { FindingDetail } from "@/components/finding-detail";
import { ProcessingTimeline } from "@/components/processing-timeline";
import { auditSteps, scenarios } from "@/lib/demo-data";
import type { DemoScenario, Finding } from "@/lib/demo-data";

type Screen = "picker" | "processing" | "dashboard" | "detail";
const MAX_FILE_BYTES = 10 * 1024 * 1024;

export default function Home() {
  const [screen, setScreen] = useState<Screen>("picker");
  const [selected, setSelected] = useState<DemoScenario>(scenarios[0]);
  const [activeStep, setActiveStep] = useState(0);
  const [finding, setFinding] = useState<Finding | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [fileError, setFileError] = useState("");

  useEffect(() => {
    if (screen !== "processing") return;
    if (activeStep >= auditSteps.length - 1) {
      const completion = window.setTimeout(() => setScreen("dashboard"), 650);
      return () => window.clearTimeout(completion);
    }
    const nextStep = window.setTimeout(() => setActiveStep((step) => step + 1), 430);
    return () => window.clearTimeout(nextStep);
  }, [activeStep, screen]);

  const selectScenario = (scenario: DemoScenario) => {
    setSelected(scenario);
    setFiles([]);
    setFileError("");
  };

  const selectFiles = (nextFiles: File[]) => {
    if (nextFiles.length > 5) {
      setFileError("Choose no more than five PDFs for one audit.");
      setFiles([]);
      return;
    }
    const invalid = nextFiles.find(
      (file) =>
        (file.type && file.type !== "application/pdf") ||
        !file.name.toLowerCase().endsWith(".pdf") ||
        file.size > MAX_FILE_BYTES,
    );
    if (invalid) {
      setFileError(`${invalid.name} must be a PDF no larger than 10 MB.`);
      setFiles([]);
      return;
    }
    setFileError("");
    setFiles(nextFiles);
  };

  const startAudit = () => {
    if (fileError) return;
    setActiveStep(0);
    setFinding(null);
    setScreen("processing");
  };

  const restart = () => {
    setScreen("picker");
    setFinding(null);
    setActiveStep(0);
  };

  if (screen === "processing") {
    return (
      <ProcessingTimeline
        activeStep={activeStep}
        files={files}
        onSkip={() => setScreen("dashboard")}
        scenario={selected}
      />
    );
  }

  if (screen === "detail" && finding) {
    return <FindingDetail finding={finding} onBack={() => setScreen("dashboard")} scenario={selected} />;
  }

  if (screen === "dashboard") {
    return (
      <AuditDashboard
        customFiles={files}
        onOpenFinding={(nextFinding) => {
          setFinding(nextFinding);
          setScreen("detail");
        }}
        onRestart={restart}
        scenario={selected}
      />
    );
  }

  return (
    <DemoPicker
      fileError={fileError}
      files={files}
      onFiles={selectFiles}
      onSelect={selectScenario}
      onStart={startAudit}
      scenarios={scenarios}
      selected={selected}
    />
  );
}
