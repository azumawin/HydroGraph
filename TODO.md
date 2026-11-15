## todo
- [x] front page displays the main measurements, but we should have another page that shows all the measurements in a more detailed way: how long ago they were measured, trends, etc.
- [ ] (core) LLM with our chosen info like research papers and general stuff about these biomarkers injected into, so that an astronaut
could ask questions about their health and the meaning of biomarkers, advice, etc. the goal is so that this is run locally.
we will use cloud for demo but we should suggest a locally ran model (different environments may have the resources necessary to
run it, but looking into some quantized models and injecting them with data may be worthwhile so this would work on whatever this
software would run on)

    they do this already so we know its a good idea
    https://spectrum.ieee.org/nasa-ai-satellite-image-analysis

    - [x] make findings ordinary messages in the chatbox, only show the negative ones
    - [ ] run a quantslop model locally ,reaach to earth for a bigger one when available
- [x] (most important) advice to the astronauts based on health conditions and parameters, like contacting the ground crew, doing something urself if u cant contact them, etc.
- [x] panel where u can see trends, health parameter risk to specific health conditions over time different time periods like half a year, monhtly, weekly, etc.
    - [x] make it dependent on the environment
