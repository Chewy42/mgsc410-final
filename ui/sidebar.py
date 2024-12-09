from shiny import ui

class InvestmentSidebar:
    def create(self):
        return ui.div(
            {"class": "sidebar"},
            ui.div(
                {"class": "refresh-button-container", "style": "margin-bottom: 15px;"},
                ui.input_action_button(
                    "refresh_dashboard",
                    "Refresh Analysis",
                    class_="btn-primary"
                )
            ),
            ui.h3("Investment Parameters", class_="sidebar-title"),
            
            # Number of Results with Max Results Option
            ui.div(
                {"class": "form-group"},
                ui.div(
                    {"style": "margin-bottom: 8px;"},
                    ui.input_checkbox(
                        "show_max_results",
                        "Show All Available Properties (up to 2000)",
                        value=False
                    )
                ),
                ui.panel_conditional(
                    "!input.show_max_results",
                    ui.input_numeric(
                        "top_n",
                        "Number of Results",
                        value=50,
                        min=5,
                        max=100,
                        step=5
                    )
                )
            ),
            
            # Price Range
            ui.div(
                {"class": "form-group"},
                ui.div(
                    {"class": "range-inputs"},
                    ui.div(
                        {"class": "range-input-group"},
                        ui.input_numeric(
                            "price_min",
                            "Min Price ($)",
                            value=300000,  # Default value
                            min=100000,
                            max=2000000,
                            step=50000
                        ),
                        ui.input_numeric(
                            "price_max",
                            "Max Price ($)",
                            value=800000,  # Default value
                            min=100000,
                            max=2000000,
                            step=50000
                        )
                    )
                )
            ),
            
            # Property Types with database values
            ui.div(
                {"class": "form-group"},
                ui.input_select(
                    "property_types",
                    "Property Types",
                    choices={
                        "": "All Types",
                        "SINGLE FAMILY": "Single Family",
                        "CONDO": "Condo",
                        "TOWNHOUSE": "Townhouse"
                    },
                    selected=["SINGLE FAMILY"],
                    multiple=True
                )
            ),
            
            # Square Footage Range
            ui.div(
                {"class": "form-group"},
                ui.div(
                    {"class": "range-inputs"},
                    ui.div(
                        {"class": "range-input-group"},
                        ui.input_numeric(
                            "sqft_min",
                            "Min Sqft",
                            value=1000,  # Default value
                            min=500,
                            max=5000,
                            step=100
                        ),
                        ui.input_numeric(
                            "sqft_max",
                            "Max Sqft",
                            value=3000,  # Default value
                            min=500,
                            max=5000,
                            step=100
                        )
                    )
                )
            ),
            
            # Location with Fresno default
            ui.div(
                {"class": "form-group"},
                ui.input_text("location", "Location (City/ZIP)", value="93720")  # Changed to Fresno ZIP
            ),
            
            # Heatmap Metric
            ui.div(
                {"class": "form-group"},
                ui.input_radio_buttons(
                    "heatmap_metric",
                    "Heatmap Metric",
                    choices={
                        "price": "Price",
                        "sqft": "Square Footage",
                        "score": "Property Score",
                        "roi": "ROI"
                    },
                    selected="price"  # Default selection
                )
            ),
            
            # Advanced Filters Toggle
            ui.div(
                {"class": "form-group"},
                ui.input_checkbox("show_advanced", "Show Advanced Filters", value=False)  # Default value
            ),
            
            # Advanced Filters Section
            ui.div(
                {"class": "advanced-filters"},
                ui.panel_conditional(
                    "input.show_advanced",
                    ui.div(
                        {"class": "form-group"},
                        ui.div(
                            {"class": "range-input-group"},
                            ui.input_numeric(
                                "roi_min",
                                "Min ROI (%)",
                                value=5,  # Default value
                                min=0,
                                max=100,
                                step=1
                            ),
                            ui.input_numeric(
                                "roi_max",
                                "Max ROI (%)",
                                value=20,  # Default value
                                min=0,
                                max=100,
                                step=1
                            )
                        )
                    ),
                    ui.div(
                        {"class": "form-group"},
                        ui.div(
                            {"class": "range-input-group"},
                            ui.input_numeric(
                                "score_min",
                                "Min Property Score",
                                value=60,  # Default value
                                min=0,
                                max=100,
                                step=1
                            ),
                            ui.input_numeric(
                                "score_max",
                                "Max Property Score",
                                value=100,  # Default value
                                min=0,
                                max=100,
                                step=1
                            )
                        )
                    ),
                    ui.div(
                        {"class": "form-group"},
                        ui.div(
                            {"class": "range-input-group"},
                            ui.input_numeric(
                                "cap_rate_min",
                                "Min Cap Rate (%)",
                                value=5,  # Default value
                                min=0,
                                max=20,
                                step=0.5
                            ),
                            ui.input_numeric(
                                "cap_rate_max",
                                "Max Cap Rate (%)",
                                value=15,  # Default value
                                min=0,
                                max=20,
                                step=0.5
                            )
                        )
                    ),
                    ui.div(
                        {"class": "form-group"},
                        ui.div(
                            {"class": "range-input-group"},
                            ui.input_numeric(
                                "price_per_sqft_min",
                                "Min Price/Sqft ($)",
                                value=100,  # Default value
                                min=50,
                                max=500,
                                step=10
                            ),
                            ui.input_numeric(
                                "price_per_sqft_max",
                                "Max Price/Sqft ($)",
                                value=300,  # Default value
                                min=50,
                                max=500,
                                step=10
                            )
                        )
                    )
                )
            )
        )
