/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import { ORBIT_SOURCE_URL } from "@plane/constants";

export function AuthFooter() {
  return (
    <div className="flex flex-col items-center gap-1 text-13 text-tertiary">
      <span>Orbit is based on Plane, licensed under AGPL-3.0.</span>
      <a href={ORBIT_SOURCE_URL} target="_blank" rel="noopener noreferrer" className="underline">
        Get the source code
      </a>
    </div>
  );
}
