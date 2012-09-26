tilecloud-chain
===============

Build the project from source
-----------------------------
```
python bootstrap.py --version 1.5.2 --distribute --download-base \
        http://pypi.camptocamp.net/distribute-0.6.22_fix-issue-227/ --setup-source \
        http://pypi.camptocamp.net/distribute-0.6.22_fix-issue-227/distribute_setup.py
./buildout/bin/buildout
```

Use it
------

Generate tiles
```
./buildout/bin/generate_tiles --config config.yaml
```

Generate WMTS capabilities
```
./buildout/bin/generate_manager --config config.yaml --generate_wmts_capabilities
```

TODO
----

- Use tilecloud from an egg
- Create hash code generator
- Generate openlayers test page
- Add cost calculator
- Implement:
    - geodata sync
    - code deploy
    - database deploy
    - run SQS tile queue filling
    - run tiles generation from SQS tile queue
- Integrate AWS host creator (buildcloud)
