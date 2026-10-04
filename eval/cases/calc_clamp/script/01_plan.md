Plan for calc.clamp:
1. Value inside [lo, hi] is returned unchanged.
2. Value below lo returns lo; value above hi returns hi.
3. Boundaries lo and hi are returned unchanged.
4. lo > hi raises ValueError.
