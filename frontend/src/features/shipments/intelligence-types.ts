export type OperationalSeverity =
  | "info"
  | "warning"
  | "critical";

export type OperationalRiskLevel =
  | "low"
  | "medium"
  | "high"
  | "critical";

export type ShipmentIdentifierKind =
  | "uuid"
  | "tracking_number"
  | "reference";

export type ShipmentOperationalIssue = {
  code: string;
  severity: OperationalSeverity;
  message: string;
  recommended_action: string;
  age_seconds: number | null;
};

export type ShipmentOperationalAnalysis = {
  shipment_id: string;
  identifier: string;
  identifier_kind: ShipmentIdentifierKind;
  has_issues: boolean;
  highest_severity: OperationalSeverity;
  risk_score: number;
  risk_level: OperationalRiskLevel;
  issues: ShipmentOperationalIssue[];
};
