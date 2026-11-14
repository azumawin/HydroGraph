import { MessageSquare } from "lucide-react";

const HealthAssistant = () => {
  return (
    <section className="vitals-dashboard-panel vitals-dashboard-health-assistant">
      <header className="vitals-dashboard-panel-header">
        <MessageSquare className="vitals-dashboard-icon" />
        <h2 className="vitals-dashboard-panel-title m-0">Health assistant</h2>
      </header>
      <div className="vitals-dashboard-panel-content min-h-0 flex-1 p-6" />
    </section>
  );
};

export default HealthAssistant;
