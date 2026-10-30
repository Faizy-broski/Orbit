/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

import type { ISvgIcons } from "../type";

export function PlaneLogo({ width = "85", height = "52", className, color = "currentColor" }: ISvgIcons) {
  return (
    <svg width={width} height={height} viewBox="0 0 85 52" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <circle cx="42.5" cy="26" r="19" stroke={color} strokeWidth="7" />
      <circle cx="56" cy="12.5" r="6" fill={color} />
    </svg>
  );
}
