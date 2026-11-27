import { Switch, Route } from "wouter";
import OperationsHub from "@/pages/operations-hub";
import AuditTrail from "@/pages/audit-trail";
import SelfServiceChat from "@/pages/self-service-chat";

function NotFound() {
  return (
    <div className="flex h-screen w-full items-center justify-center">
      <p className="text-muted-foreground">404 — Page not found</p>
    </div>
  );
}

export default function App() {
  return (
    <Switch>
      <Route path="/" component={OperationsHub} />
      <Route path="/audit" component={AuditTrail} />
      <Route path="/chat" component={SelfServiceChat} />
      <Route component={NotFound} />
    </Switch>
  );
}
