"""Published optimal tour lengths for TSPLIB instances.

These are external reference data, not results produced by this project. They
are recorded here so the test suite can cross-check two independent facts:

1. the optimal tour length published for an instance, and
2. the cost this project computes when scoring the accompanying published
   ``.opt.tour`` file with its own distance implementation.

If those disagree, either the distance convention is wrong or the tour parser
is -- and the test reports both numbers so it is clear which. That is the whole
point of keeping the values here rather than asserting whatever the code happens
to produce.

Source: TSPLIB95, Gerhard Reinelt, Universitaet Heidelberg.
"""

#: instance name -> published optimal tour length, in that instance's own units
PUBLISHED_OPTIMA: dict[str, int] = {
    "eil51": 426,
    "berlin52": 7542,
    "st70": 675,
    "pr76": 108159,
    "kroA100": 21282,
}
