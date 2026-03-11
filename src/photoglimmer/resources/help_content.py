# ######################################################################################
# Encapsulation for the text content of our Help Dialog . Thi scan be easily imported there
# We use a function or a raw string with format keys. 
# Using a function is safer to avoid conflicts with CSS curly braces { }.
# ######################################################################################

def get_help_html(palette):
    """
    Returns the HTML string with colors injected from the provided palette dictionary.
    """
    return f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body {{ 
        font-family: sans-serif; 
        color: {palette.get("@text_primary", "#000000")}; 
        background-color: {palette.get("@bg_primary", "#ffffff")}; 
        line-height: 1.6; 
        margin:10px;
    }}
    
    /* Headings get the accent color (if you have one, or secondary text) */
    h1 {{ 
        color: {palette.get("@text_primary", "#000000")}; 
        border-bottom: 2px solid {palette.get("@border", "#ccc")}; 
        padding-bottom: 10px; 
    }}

    


    h2, h3 {{ 
        color: {palette.get("@text_secondary", "#555555")}; 
        margin-top: 30px; 
    }}

    h2{{background-color: "#8caa97"; color:"#";
      margin-right:100px; 
      border-top-right-radius:10px;
      border-bottom-right-radius:5px }}

    /* Keycaps (Keyboard shortcuts) */
    .key {{ 
        background-color: {palette.get("@bg_tertiary", "#eee")}; 
        border: 1px solid {palette.get("@border", "#ccc")}; 
        border-radius: 4px; 
        padding: 2px 6px; 
        font-family: monospace; 
        font-weight: bold; 
        color: {palette.get("@text_primary", "#000")}; 
    }}

    /* Note Box */
    .note {{ 
        background-color: {palette.get("@bg_secondary", "#f0f0f0")}; 
        padding: 10px; 
        border-left: 4px solid {palette.get("@text_secondary", "#888")}; 
        margin: 15px 0; 
    }}
    
    ul {{ padding-left: 20px; }}
    li {{ margin-bottom: 8px; }}
    strong {{ color: {palette.get("@text_primary", "#000")}; font-weight: bold; }}
</style>
</head>
<body>

<h1>Photoglimmer Guide</h1>
<p>Photoglimmer automatically distinguishes between <strong>People</strong> and <strong>Backgrounds</strong> It's main
goals are <strong>Privacy</strong> and <strong>Ease of Use</strong> for amateur photographers like myself.
</p>

<h2>1. 🎨 Basics 🎨</h2>
<ul>
    <li><strong>Open An image</strong> Either using the menu, button, or drag and drop.</li>
    <li><strong>Frame Persons</strong> Click on image and drag mouse to draw rectangular frames around one or more persons.</li>
    <li><strong>Tweak Color Values</strong> Select a frame and use the Sliders to enhance people in them.</li>
    <li><strong>Multiple Frames</strong> You can apply  different settings to each frame.</li>
    <li><strong>To select a frame</strong>, Either click on it or select from the list on the left sidebar.</li>
    <li><strong>Export the Image</strong>Click the export button to save the result</li>

</ul>

<h2>2. Refinements</h2>
<h3>🎨 Smooth Blending</h3>
<p>Use the <strong>Feathering</strong> slider from <strong>Mask Edge</strong> panel for 
    smooth blending with background.
<h3>🎨 Editng the Background</h3>
<p>Slect <strong>background</strong> layer from the <strong>Frames List on the Left Sidebar</strong>
<p> This is also where  you can add a  <strong>background blur</strong>   to your image
<h3>🎨 Enhancing the Mask</h3>
<p>If the AI fails to get perfect selection you can :
    <li> Use the <strong>Mask Edge </strong> at the top of right sidebar </li>  
    <li>OR</li>
    <li> Click the <strong>Manual Mask</strong> button in the toolbar</li> 
</p>
<h3>🎨 Manual Mask Editing</h3>
<p>Clicking the <strong>Manual Mask</strong>button will give you options to paint or erase with mouse.
    You can do it with crude lines. Increase feathering as above if needed.  Click the 
    button again when done.
</p>
<h3>🎨 Uncluttering the Canvas</h3>
<p>Clicking the <strong>👁 Hide Frames</strong> button in tool bar hides all frame outlines. You can still use the sliders. 
    Click the button again to bring back the frames*
    <br/>* You can select frames from the list even if  they are hidden 
</p> 

<h3>🎨 Face Vs Body</h3>
<p> You can create a small frame around the head and a larger frame around the whole body (body+head). <br/>
    You might need to increase feathering on the face  frame for good blending.(Mask Edge panel) 
</p> 

<h3>🎨 Explore the options</h3>
<p> Expand the <strong>collapsed Panels</strong>  on <strong>right sidebar</strong> to see advance options  
</p>  

<h2>3. Take a  Peek</h2>
<h3>🎨 Uncluttering the Canvas</h3>
<p>Clicking the <strong>👁 Hide Frames</strong> button in tool bar hides all frame outlines. You can still use the sliders. 
    Click the button again to bring back the frames*
    <br/>* You can select frames from the list even if  they are hidden 
</p> 

<h3>🎨 See the Original Image</h3>
<p>Click the <strong>Middle Mouse Button</strong> to peek at the original image anytime. <br/>
    You can also open the original image from Tools Menu
 </p>

 
 <h2>4. Scopes Legend</h2>

 <h3>🎨 What applies Where </h3>

 <p> Each panel in the right sidebar  shows a small icon to tell the scope of that operation</p>
 <p>
  👤 : Central face in that frame ,  <br/> 
  📄 : All persons in  selected frame ,  <br/> 
  🌐 : On the whole image    
 </p> 

  
<h2>5. Look & Feel</h2>
<p> Use <strong>Tools &gt; Preferences</strong>  menu to change the color theme of the application. 
</p>

<h2>6. File Locations</h2>
<p>
<li>  Use <strong>Tools &gt; Preferences</strong>  menu to change the default location file dialogues. </li>
<li>  Use <strong>Tools &gt; Openc Containing Folder</strong> to open the folder containing your source image. </li>
</p>

<h2>7. Privacy and feedback </h2>


<h3>🎨 Privacy </h3>
<p class="note">Privacy Note: All parts of Photoglimmer are self-contianed. Nothing leaves your computer.</p>


<h3>🎨 Feature Request and Bug Reporting </h3>
<p>Right now , this  the only place  for
 this is <a href="https://github.com/codecliff/PhotoGlimmer/issues">github issue page</a> of this project 
</p>


 



<h2>8. Keyboard Shortcuts</h2>


<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
    <tr style="border-bottom: 1px solid #444; text-align: left;">
        <th style="padding: 8px;">Action</th>
        <th style="padding: 8px;">Shortcut</th>
    </tr>

    <tr>
        <td style="padding: 6px;">Open Image</td>
        <td><span class="key">Ctrl</span> + <span class="key">O</span></td>
    </tr>
    <tr>
        <td style="padding: 6px;">Export Image</td>
        <td><span class="key">Ctrl</span> + <span class="key">E</span> 
        OR 
        <span class="key">Ctrl</span> + <span class="key">S</span></td>
    </tr>
    <tr>
        <td style="padding: 6px;">Preferences</td>
        <td><span class="key">Ctrl</span> + <span class="key">P</span></td>
    </tr>

    <tr>
        <td style="padding: 6px;">Undo</td>
        <td><span class="key">Ctrl</span> + <span class="key">Z</span></td>
    </tr>
    <tr>
        <td style="padding: 6px;">Redo</td>
        <td><span class="key">Ctrl</span> + <span class="key">Y</span></td>
    </tr>

    <tr>
        <td style="padding: 6px;">Hide Frames</td>
        <td><span class="key">H</span></td>
    </tr>
    <tr>
        <td style="padding: 6px;">Zoom In</td>
        <td><span class="key">Ctrl</span> + <span class="key">+</span></td>
    </tr>
    <tr>
        <td style="padding: 6px;">Zoom Out</td>
        <td><span class="key">Ctrl</span> + <span class="key">-</span></td>
    </tr>
    <tr>
        <td style="padding: 6px;">Fit to Screen</td>
        <td><span class="key">Ctrl</span> + <span class="key">0</span></td>
    </tr>

    <tr>
        <td style="padding: 6px;">User Guide</td>
        <td><span class="key">F1</span>
        OR 
        <span class="key">Ctrl</span> + <span class="key">H</span> 
        
        </td>
    </tr>

    <tr><td style="padding: 6px;">&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td style="padding: 6px;">&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td style="padding: 6px;">&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td style="padding: 6px;">&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td style="padding: 6px;">&nbsp;</td><td>&nbsp;</td></tr>
</table>




<p class="Note"> &copy; Rahul Singh (2026)</p>


</body>
</html>

"""
