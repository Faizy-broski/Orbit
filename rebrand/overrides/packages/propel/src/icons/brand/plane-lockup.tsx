/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

import type { ISvgIcons } from "../type";

export function PlaneLockup({ width = "190", height = "53", className, color = "currentColor" }: ISvgIcons) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 190 53"
      preserveAspectRatio="xMinYMid meet"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <circle cx="26" cy="27" r="19" stroke={color} strokeWidth="7" />
      <circle cx="39.5" cy="13.5" r="6" fill={color} />
      <text x="62" y="43" fill={color} fontFamily="Inter, system-ui, sans-serif" fontSize="46" fontWeight="600">
        Orbit
      </text>
    </svg>
  );
}
