wmts_get_capabilities_template = """<?xml version="1.0" encoding="UTF-8"?>
<Capabilities version="1.0.0" xmlns="http://www.opengis.net/wmts/1.0" xmlns:ows="http://www.opengis.net/ows/1.1"
              xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xmlns:gml="http://www.opengis.net/gml"
              xsi:schemaLocation="http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd">
  <ows:ServiceIdentification> </ows:ServiceIdentification>
  <ows:ServiceProvider> </ows:ServiceProvider>
  <ows:OperationsMetadata>
    <ows:Operation name="GetCapabilities">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="{{getcapabilities}}">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>
        </ows:HTTP>
      </ows:DCP>
    </ows:Operation>
    <ows:Operation name="GetTile">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="{{gettile}}">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>
        </ows:HTTP>
      </ows:DCP>
    </ows:Operation>
  </ows:OperationsMetadata>
  <!-- <ServiceMetadataURL xlink:href="" /> -->
  <Contents>
    {% for layername, layer in layers.items() %}
    <Layer>
      <ows:Title>{{layername}}</ows:Title>
      <ows:Identifier>{{layername}}</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>{{layer['wmts']['style']}}</ows:Identifier>
      </Style>
      <Format>{{layer['mime_type']}}</Format> {%
      for dimension in layer['dimensions'] %}
      <Dimension>
        <ows:Identifier>{{dimension['name']}}</ows:Identifier>
        <Default>{{dimension['default']}}</Default> {%
            for value in dimension['values'] %}
        <Value>{{value}}</Value> {%
            endfor %}
      </Dimension> {%
      endfor %}
      <ResourceURL format="{{layer['mime_type']}}" resourceType="tile"
                   template="{{gettile}}/1.0.0/{{layername}}/{{layer['wmts']['style']}}/{%
                        for dimension in layer['dimensions']
                            %}{{('{' + dimension['name'] + '}')}}{%
                        endfor
                   %}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.{{layer['extension']}}" />
      <TileMatrixSetLink>
        <TileMatrixSet>{{layer["grid"]}}</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>
    {% endfor %}

    {% for grid in grids.values() %}
    <TileMatrixSet>
      <ows:Identifier>{{grid['name']}}</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:{{
            grid['srs'].replace(':', '::')
      }}</ows:SupportedCRS>
      {% for i, resolution in enumerate(grid['resolutions']) %}
      <TileMatrix>
        <ows:Identifier>{{i}}</ows:Identifier>
        <ScaleDenominator>{{resolution / 0.00028}}</ScaleDenominator>
        <TopLeftCorner>{{grid['bbox'][0]}} {{grid['bbox'][3]}}</TopLeftCorner>
        <TileWidth>{{grid['tile_size']}}</TileWidth>
        <TileHeight>{{grid['tile_size']}}</TileHeight>
        <MatrixWidth>{{
            ceil(
                (grid['bbox'][2]-grid['bbox'][0]) /
                resolution / grid['tile_size'])
        }}</MatrixWidth>
        <MatrixHeight>{{
            ceil(
                (grid['bbox'][3]-grid['bbox'][1]) /
                resolution / grid['tile_size'])
        }}</MatrixHeight>
      </TileMatrix>
      {% endfor %}
    </TileMatrixSet>
    {% endfor %}
  </Contents>
</Capabilities>"""
