
# we need an endpoint so the astronaut could upload their health history that we could use a baseline
# user needs to be authenticated so we get id from request header
# units are assumed to be from SI standard
# idempotency key would be realistic since microcontrollers retry, but not needed for demo
# frontend ingests these
## singular channel/parameter reading shape, 

```json
{                                                                     
"channel": "bp_systolic",
"value": 118,
"unit": "mmHg",
"evaluation": "optimal" | "normal" | "unusual" | "critical",
"measured_at": "2026-11-08T07:12:00Z",
"name": "Blood pressure (systolic)",
"domain": "cardiovascular",
"body_regions": ["heart", "chest"],
"explanation": "Why this is measured, what it means…",
}                                                                                                                                                
```

## predefined environments, fetched once on environnmen switch
comm delay is a range actually not a specific number, i think we just simplify it to a number for the demo

example json:
```json
{
  "environments": [
    {
      "id": "lunar_surface",
      "gravity_g": 0.166,
      "comm_delay_s": 2.6
    },
    {
      "id": "moon",
      "gravity_g": 0.377,
      "comm_delay_s": 600
    }
  ]
}
```

# backend receives this
sensors -> microcontroller makes the required shape -> backend

for demo we will just fake it wiht a fake client
```json
{                                                                     
"channel": "bp_systolic",
"value": 118,
"evaluation": "optimal" | "normal" | "unusual" | "critical"
"measured_at": "2026-11-08T07:12:00Z",
}                                                                                                                                                
```

body_regions is what makes the clickable body figure a data-driven feature instead of a hardcoded SVG switch statement. citations per channel is what makes the pitch line in idea.md ("every
threshold hardcoded from cited research") literally checkable by a judge — it's in the API.
