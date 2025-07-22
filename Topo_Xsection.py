import rasterio
import numpy as np
import matplotlib.pyplot as plt
from rasterio.plot import show
from skimage.draw import line
import streamlit as st
import ezdxf
import tempfile
import os

st.title("Plotting Topography Cross Section in DXF")

# File uploader for TIFF file (corrected from "Excel file" in original code)
uploaded_file = st.file_uploader("Upload TIFF file", type=["tif", "tiff"])

# Input fields for start and end points
st.subheader("Enter Cross-Section Line Coordinates")
col1, col2 = st.columns(2)
with col1:
    start_x = st.text_input("Input the Easting (X) of your start point here")
    start_y = st.text_input("Input the Northing (Y) of your start point here")
with col2:
    end_x = st.text_input("Input the Easting (X) of your end point here")
    end_y = st.text_input("Input the Northing (Y) of your end point here")

# Validation function
def is_valid_coordinate(value, name):
    try:
        return float(value)
    except ValueError:
        st.error(f"{name} must be a numeric value")
        return None

# Function to plot the Digital Elevation Model (DEM)
def plot_dem(dem_data, transform):
    fig, ax = plt.subplots(figsize=(10, 6))
    img = ax.imshow(dem_data, cmap='terrain', aspect='auto')
    plt.colorbar(img, label='Elevation (m)')
    plt.title('Digital Elevation Model')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    return fig

# Function to extract elevation values along a line
def extract_cross_section(dem_data, start_pixel, end_pixel):
    rr, cc = line(start_pixel[0], start_pixel[1], end_pixel[0], end_pixel[1])
    return dem_data[rr, cc]

# Function to plot the cross-section
def plot_cross_section(elevation_values):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(elevation_values)
    ax.set_title('Cross-Section of DEM')
    ax.set_xlabel('Distance along line (pixels)')
    ax.set_ylabel('Elevation (m)')
    ax.grid(True)
    return fig

# Main processing logic
if uploaded_file is not None and all([start_x, start_y, end_x, end_y]):
    # Validate inputs
    start_x_val = is_valid_coordinate(start_x, "Start Easting")
    start_y_val = is_valid_coordinate(start_y, "Start Northing")
    end_x_val = is_valid_coordinate(end_x, "End Easting")
    end_y_val = is_valid_coordinate(end_y, "End Northing")

    if None not in (start_x_val, start_y_val, end_x_val, end_y_val):
        # Check if integer parts have same number of digits
        def get_integer_digits(num):
            return len(str(int(abs(float(num)))))
        
        x_digits = get_integer_digits(start_x_val)
        y_digits = get_integer_digits(start_y_val)
        end_x_digits = get_integer_digits(end_x_val)
        end_y_digits = get_integer_digits(end_y_val)
        
        if x_digits == y_digits == end_x_digits == end_y_digits:
            # Calculate section length using Pythagorean theorem
            section_length = np.sqrt((end_x_val - start_x_val)**2 + (end_y_val - start_y_val)**2)
            st.write(f"Length of the cross section: {section_length:.2f} meters")

            # Read the uploaded TIFF file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tif") as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_file_path = tmp_file.name

            try:
                with rasterio.open(tmp_file_path) as src:
                    dem_data = src.read(1)  # Read the first band
                    transform = src.transform

                    # Plot DEM
                    fig_dem = plot_dem(dem_data, transform)
                    st.pyplot(fig_dem)
                    plt.close(fig_dem)

                    # Convert geographic coordinates to pixel coordinates
                    start_row, start_col = rasterio.transform.rowcol(transform, start_x_val, start_y_val)
                    end_row, end_col = rasterio.transform.rowcol(transform, end_x_val, end_y_val)

                    # Round to nearest integer for pixel coordinates
                    start_pixel = (int(round(start_row)), int(round(start_col)))
                    end_pixel = (int(round(end_row)), int(round(end_col)))

                    st.write(f"Start Pixel: {start_pixel}")
                    st.write(f"End Pixel: {end_pixel}")

                    # Extract and plot cross-section
                    elevation_values = extract_cross_section(dem_data, start_pixel, end_pixel)
                    fig_cross = plot_cross_section(elevation_values)
                    st.pyplot(fig_cross)
                    plt.close(fig_cross)

                    # Export cross-section to DXF
                    doc = ezdxf.new(dxfversion='R2010')
                    msp = doc.modelspace()
                    points = [(i, elevation) for i, elevation in enumerate(elevation_values)]
                    msp.add_lwpolyline(points, dxfattribs={'layer': 'cross_section'})

                    # Save DXF to temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as dxf_tmp:
                        doc.saveas(dxf_tmp.name)
                        dxf_file_path = dxf_tmp.name

                    # Provide download button for DXF
                    with open(dxf_file_path, 'rb') as f:
                        st.download_button(
                            label="Download DXF file",
                            data=f,
                            file_name="cross_section.dxf",
                            mime="application/dxf"
                        )

                    # Clean up temporary files
                    os.unlink(tmp_file_path)
                    os.unlink(dxf_file_path)

            except Exception as e:
                st.error(f"Error processing TIFF file: {str(e)}")
        else:
            st.error("All coordinates must have the same number of digits in their integer parts.")
else:
    if uploaded_file is None:
        st.info("Please upload a TIFF file.")
    if not all([start_x, start_y, end_x, end_y]):
        st.info("Please provide all coordinate inputs.")

