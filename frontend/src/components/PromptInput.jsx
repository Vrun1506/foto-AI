import "./PromptInput.css"

export default function PromptInput() {
    return (
        <form id="prompt-submit-form">
            <input type="text" id="prompt" name="prompt" required placeholder="What would you like to do to your image?" />
            <input type="submit" id="submit-button" value="Generate"/>
        </form>
    )
}