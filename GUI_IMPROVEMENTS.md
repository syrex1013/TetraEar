# GUI Improvements Applied

## 1. Enhanced Data Visualization
- **Data Column**: Added a dedicated "Data" column to the frames table.
- **Meaningful Interpretation**: 
  - Displays decrypted text if available.
  - Shows SDS (Short Data Service) messages.
  - Formats raw MAC PDU data as hex strings.
  - Fallback to raw bits if no other data is available.

## 2. Color Coding
- **Frame Types**: Rows are now color-coded based on frame type for easier visual identification:
  - **MAC-RESOURCE**: Dark Blue
  - **MAC-BROADCAST**: Dark Yellow/Orange
  - **MAC-FRAG**: Dark Green
  - **MAC-SUPPL**: Dark Purple
  - **MAC-U-SIGNAL**: Dark Red

## 3. Voice Listening
- **Live Audio**: Implemented FM demodulation of the TETRA signal to allow monitoring of the digital noise/signal presence.
- **Mute Control**: Added a "Mute" button to the Options panel to toggle audio on/off.

## 4. Real-time Updates
- **Optimized Display**: The table updates in real-time with the decoded data.
- **Auto-scroll**: Keeps the latest frames in view.

## 5. Code Cleanup
- Fixed indentation errors and removed duplicate/garbage code in the `on_frame` method.
