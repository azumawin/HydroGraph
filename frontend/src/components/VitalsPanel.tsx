import { useState } from "react";
import type { ComponentType } from "react";
import { MAIN_PANEL_TABS } from "../Constants.ts";
import type { MainPanelTabId } from "../Constants.ts";
import MeasurementsTable from "./MeasurementsTable.tsx";
import TrendsTab from "./TrendsTab.tsx";
import VitalsReadings from "./VitalsReadings.tsx";
import "../assets/css/VitalsPanel.css";

const TAB_CONTENT: Record<MainPanelTabId, ComponentType> = {
  vitals: VitalsReadings,
  measurements: MeasurementsTable,
  trends: TrendsTab,
};

const VitalsPanel = () => {
  const [activeTabId, setActiveTabId] = useState<MainPanelTabId>(MAIN_PANEL_TABS[0].ID);

  const ActiveTabContent = TAB_CONTENT[activeTabId];

  return (
    <section className="vitals-dashboard-panel vitals-dashboard-vitals row-span-2">
      <div className="vitals-dashboard-panel-tabs" role="tablist">
        {MAIN_PANEL_TABS.map((tab) => (
          <button
            key={tab.ID}
            id={`vitals-dashboard-tab-${tab.ID}`}
            type="button"
            role="tab"
            aria-selected={tab.ID === activeTabId}
            aria-controls="vitals-dashboard-tab-panel"
            className={`vitals-dashboard-panel-tab${tab.ID === activeTabId ? " is-active" : ""}`}
            onClick={() => setActiveTabId(tab.ID)}
          >
            {tab.LABEL}
          </button>
        ))}
      </div>
      <div
        id="vitals-dashboard-tab-panel"
        className="vitals-dashboard-panel-tab-content"
        role="tabpanel"
        aria-labelledby={`vitals-dashboard-tab-${activeTabId}`}
      >
        <ActiveTabContent />
      </div>
    </section>
  );
};

export default VitalsPanel;
