from shiny import ui
import folium
from folium.plugins import HeatMap, MarkerCluster
from geopy.geocoders import Nominatim

class MainPanel:
    @staticmethod
    def create():
        try:
            return ui.div(
                {"class": "grid-container"},
                # Add script reference
                ui.tags.script(src="service.js"),
                # Geographic Distribution Card
                ui.div(
                    {"class": "chart-card map-card"},
                    ui.div(
                        {"class": "card-header"},
                        ui.h3("Geographic Distribution"),
                        ui.div(
                            {"class": "chart-controls"},
                            ui.input_select(
                                "heatmap_metric",
                                None,
                                choices={
                                    "price": "Price Heatmap",
                                    "fair_price": "Fair Price Heatmap",
                                    "price_diff": "Price Difference",
                                    "sqft": "Square Footage",
                                    "score": "Investment Score",
                                    "roi": "ROI Distribution"
                                },
                                selected="price"
                            )
                        )
                    ),
                    # Remove the hardcoded height style to use CSS
                    ui.output_ui("heatmap")
                ),
                # Product Search and Table Card
                ui.div(
                    {"class": "chart-card products-card"},
                    ui.div(
                        {"class": "card-header"},
                        ui.h3("Amazon Products"),
                        ui.div(
                            {"class": "search-container"},
                            ui.input_text(
                                "product_search",
                                "",
                                placeholder="Search products...",
                                class_="search-input"
                            )
                        )
                    ),
                    ui.div(
                        {"class": "table-container"},
                        ui.output_table("products_table")
                    )
                ),
                # Investment Opportunities Card
                MainPanel.opportunities_card()
            )
        except Exception as e:
            return ui.div(
                ui.h3("Error loading dashboard"),
                ui.p(str(e))
            )

    @staticmethod
    def get_coordinates(zip_code):
        """Get coordinates for ZIP code with fallback to hardcoded values"""
        # Hardcoded coordinates for common ZIP codes
        ZIP_COORDINATES = {
            '93720': (36.8530, -119.7743),  # Fresno, CA
            '92866': (33.7879, -117.8531),  # Orange, CA
            '92867': (33.8089, -117.8281),
            '92868': (33.7789, -117.8831),
            '92869': (33.7919, -117.7531),
        }
        
        try:
            # First try hardcoded coordinates
            if zip_code in ZIP_COORDINATES:
                return ZIP_COORDINATES[zip_code]
                
            # If not in hardcoded list, try geocoding
            geolocator = Nominatim(user_agent="real_estate_optimizer")
            location = geolocator.geocode({"postalcode": zip_code, "country": "US"})
            if location:
                return location.latitude, location.longitude
                
            # If geocoding fails, use a default location (Orange, CA)
            print(f"Using default coordinates for ZIP: {zip_code}")
            return ZIP_COORDINATES['92866']
            
        except Exception as e:
            print(f"Error getting coordinates: {str(e)}")
            # Return default coordinates on error
            return ZIP_COORDINATES['92866']

    @staticmethod
    def create_heatmap(center_zip, data_points, metric="price"):
        """Create a folium heatmap with clickable markers centered on ZIP code"""
        try:
            # Get center coordinates
            coordinates = MainPanel.get_coordinates(center_zip)
            if not coordinates:
                if data_points:
                    coordinates = (data_points[0][0], data_points[0][1])
                else:
                    coordinates = (33.7879, -117.8531)
            
            latitude, longitude = coordinates
            
            m = folium.Map(location=[latitude, longitude], 
                          zoom_start=11,
                          tiles='cartodbpositron',
                          width='100%',
                          height='400px')
            
            if data_points:
                print(f"Processing {len(data_points)} data points")
                
                marker_cluster = MarkerCluster(name="Properties")
                heatmap_data = []
                
                for point in data_points:
                    lat, lon, intensity = point[:3]
                    property_data = point[3] if len(point) > 3 else None
                    
                    heatmap_data.append([float(lat), float(lon), float(intensity)])
                    
                    if property_data:
                        # Format values with error handling
                        def safe_format(value, format_str="{:,.0f}"):
                            try:
                                return format_str.format(value) if value is not None else "N/A"
                            except:
                                return "N/A"
                        
                        # Calculate additional metrics
                        price_per_sqft = property_data['price'] / property_data['sqft'] if property_data['price'] and property_data['sqft'] else None
                        cap_rate = property_data.get('cap_rate', 0)
                        monthly_mortgage = (property_data['price'] * 0.8 * 0.06 / 12) if property_data['price'] else None  # Rough estimate: 80% LTV, 6% rate
                        
                        # Create Google Maps link
                        maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                        
                        # Enhanced popup content with more details
                        popup_content = f"""
                            <div style="font-family: Arial, sans-serif; min-width: 300px; max-width: 400px;">
                                <h4 style="margin: 0 0 10px 0; color: #1a237e; border-bottom: 2px solid #eef2f7; padding-bottom: 5px;">
                                    {property_data.get('address', 'N/A')}
                                </h4>
                                
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                    <div style="margin: 5px 0;">
                                        <b>Price:</b> ${safe_format(property_data.get('price'))}
                                    </div>
                                    <div style="margin: 5px 0;">
                                        <b>Fair Price:</b> ${safe_format(property_data.get('fair_price'))}
                                    </div>
                                    <div style="margin: 5px 0;">
                                        <b>Price Difference:</b> {property_data.get('price_diff')}
                                    </div>
                                    <div style="margin: 5px 0;">
                                        <b>Difference %:</b> {property_data.get('price_diff_pct')}
                                    </div>
                                    
                                    <div style="margin: 5px 0;">
                                        <b>Type:</b> {property_data.get('type', 'N/A')}
                                    </div>
                                    
                                    <div style="margin: 5px 0;">
                                        <b>Square Feet:</b> {safe_format(property_data.get('sqft'))}
                                    </div>
                                    <div style="margin: 5px 0;">
                                        <b>Price/Sqft:</b> ${safe_format(price_per_sqft, "{:.2f}")}
                                    </div>
                                    
                                    <div style="margin: 5px 0;">
                                        <b>Beds:</b> {safe_format(property_data.get('beds'))}
                                    </div>
                                    <div style="margin: 5px 0;">
                                        <b>Baths:</b> {safe_format(property_data.get('baths'))}
                                    </div>
                                    
                                    <div style="margin: 5px 0;">
                                        <b>Year Built:</b> {safe_format(property_data.get('year_built'))}
                                    </div>
                                    <div style="margin: 5px 0;">
                                        <b>Investment Score:</b> {safe_format(property_data.get('score'), "{:.1f}")}/10
                                    </div>
                                </div>
                                
                                <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #eef2f7;">
                                    <h5 style="margin: 0 0 5px 0; color: #1a237e;">Investment Analysis</h5>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                        <div style="margin: 5px 0;">
                                            <b>Monthly Rent:</b> ${safe_format(property_data.get('rent'))}
                                        </div>
                                        <div style="margin: 5px 0;">
                                            <b>Cap Rate:</b> {safe_format(cap_rate, "{:.1f}")}%
                                        </div>
                                        
                                        <div style="margin: 5px 0;">
                                            <b>Est. Mortgage:</b> ${safe_format(monthly_mortgage)}
                                        </div>
                                        <div style="margin: 5px 0;">
                                            <b>Cash Flow:</b> ${safe_format(property_data.get('rent', 0) - (monthly_mortgage or 0))}
                                        </div>
                                    </div>
                                </div>
                                
                                <div style="margin-top: 10px; text-align: center;">
                                    <a href="{maps_url}" target="_blank" style="
                                        display: inline-block;
                                        padding: 8px 16px;
                                        background: #1a237e;
                                        color: white;
                                        text-decoration: none;
                                        border-radius: 4px;
                                        font-size: 14px;
                                        margin-top: 5px;">
                                        View on Google Maps 🗺️
                                    </a>
                                </div>
                            </div>
                        """
                        
                        # Create marker with custom icon
                        icon = folium.Icon(
                            color='red' if property_data.get('score', 0) >= 7 else 'orange',
                            icon='home',
                            prefix='fa'
                        )
                        
                        # Add marker to cluster
                        folium.Marker(
                            location=[lat, lon],
                            popup=folium.Popup(popup_content, max_width=400),
                            icon=icon
                        ).add_to(marker_cluster)
                
                # Add marker cluster to map
                marker_cluster.add_to(m)
                
                # Add heatmap if we have data
                if heatmap_data:
                    print(f"Creating heatmap with {len(heatmap_data)} points")
                    
                    max_value = max(point[2] for point in heatmap_data)
                    if max_value > 0:
                        normalized_points = [[p[0], p[1], p[2]/max_value] for p in heatmap_data]
                        
                        HeatMap(
                            normalized_points,
                            name="Heatmap",
                            min_opacity=0.3,
                            max_zoom=18,
                            radius=25,
                            blur=15,
                            gradient={
                                'price': {0.4: 'blue', 0.65: 'lime', 0.85: 'yellow', 1: 'red'},
                                'sqft': {0.4: 'purple', 0.65: 'cyan', 0.85: 'green', 1: 'yellow'},
                                'score': {0.4: 'blue', 0.65: 'green', 0.85: 'yellow', 1: 'red'},
                                'roi': {0.4: 'blue', 0.65: 'purple', 0.85: 'orange', 1: 'red'}
                            }.get(metric, {0.4: 'blue', 0.65: 'lime', 0.85: 'yellow', 1: 'red'})
                        ).add_to(m)
                
                folium.LayerControl().add_to(m)
            
            return m._repr_html_()
            
        except Exception as e:
            print(f"Error creating heatmap: {str(e)}")
            return f"<div>Error creating heatmap: {str(e)}</div>"

    @staticmethod
    def opportunities_card():
        return ui.div(
            {"class": "chart-card opportunities-card"},
            ui.div(
                {"class": "card-header"},
                ui.h3("Premium Investment Opportunities"),
                ui.div(
                    {"class": "chart-controls"},
                    ui.input_select(
                        "sort_criteria",
                        None,
                        choices={
                            "score": "Investment Score ↓",
                            "roi_potential": "ROI Potential ↓",
                            "cap_rate": "Cap Rate ↓",
                            "price_asc": "Price (Low to High)",
                            "price_desc": "Price (High to Low)"
                        },
                        selected="score"
                    )
                )
            ),
            ui.div(
                {"class": "table-container"},
                ui.output_table("opportunities_table", bordered=True, compact=True)
            )
        )
