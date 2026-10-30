/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

import { IconWrapper } from "../icon-wrapper";
import type { ISvgIcons } from "../type";

export function PlaneNewIcon({ color = "currentColor", ...rest }: ISvgIcons) {
  return (
    <IconWrapper color={color} {...rest}>
      <circle cx="8" cy="8" r="5.3" stroke={color} strokeWidth="2" />
      <circle cx="11.8" cy="4.2" r="1.7" fill={color} />
    </IconWrapper>
  );
}
