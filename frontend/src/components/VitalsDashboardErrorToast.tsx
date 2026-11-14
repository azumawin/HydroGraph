import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { VITALS_NOTIFICATIONS } from "../Constants.ts";

type VitalsDashboardErrorToastProps = {
  failedReadings: string;
};

const VitalsDashboardErrorToast = ({ failedReadings }: VitalsDashboardErrorToastProps) => {
  const [isToastVisible, setIsToastVisible] = useState(true);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setIsToastVisible(false);
    }, VITALS_NOTIFICATIONS.ERROR_DURATION_MS);

    return () => window.clearTimeout(timeoutId);
  }, []);

  if (!isToastVisible) return null;

  return (
    <div className="vitals-dashboard-error-toast" role="alert">
      <p className="vitals-dashboard-error-toast-message">
        Could not load {failedReadings}. Reload to try again.
      </p>
      <button
        type="button"
        className="vitals-dashboard-error-toast-dismiss"
        aria-label="Dismiss notification"
        onClick={() => setIsToastVisible(false)}
      >
        <X className="vitals-dashboard-error-toast-dismiss-icon" />
      </button>
    </div>
  );
};

export default VitalsDashboardErrorToast;
