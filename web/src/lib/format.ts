/**
 * Objective formatting.
 *
 * A cost only means something alongside its unit. TSPLIB instances carry an
 * abstract integer cost with no physical interpretation, so presenting one as
 * kilometres is wrong by a factor of 1000 and invents a precision the data does
 * not have. This is the display-side counterpart of core/model/units.py.
 */

import { DistanceMatrix } from '../types';

export type Units = DistanceMatrix['units'];

/** Format an objective value in its own units. Never converts across units. */
export function formatObjective(value: number, units: Units): string {
  switch (units) {
    case 'metres':
      return value >= 1000
        ? `${(value / 1000).toFixed(2)} km`
        : `${Math.round(value)} m`;
    case 'seconds': {
      const mins = Math.round(value / 60);
      return mins >= 60 ? `${(mins / 60).toFixed(1)} h` : `${mins} min`;
    }
    case 'tsplib_units':
      // Deliberately unitless, matching how TSPLIB publishes its optima.
      return `${Math.round(value).toLocaleString()}`;
  }
}

/** Short unit label for axes and table headers. */
export function unitLabel(units: Units): string {
  return units === 'tsplib_units' ? 'units' : units;
}
