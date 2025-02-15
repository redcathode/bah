<script>
    let conversations = [];

    async function fetchConversations() {
        if (typeof window !== 'undefined') { // Check if running in browser
            const response = await fetch('http://192.168.1.245:5000/api/conversations');
            conversations = await response.json();
        } else {
            conversations = [ // Placeholder for server-side rendering
                { id: 1, sender: 'Server Side User 1', subject: 'SSR Email 1', date: 'Now' },
                { id: 2, sender: 'Server Side User 2', subject: 'SSR Email 2', date: 'Then' },
            ];
        }
    }

    fetchConversations();
</script>

<div class="conversations-container">
    <h2>Conversation History</h2>
    {#each conversations as conversation}
        <div class="conversation-item">
            <p><strong>Sender:</strong> {conversation.sender}</p>
            <p><strong>Subject:</strong> {conversation.subject}</p>
            <p><strong>Date:</strong> {conversation.date}</p>
        </div>
    {/each}
</div>

<style>
    .conversations-container {
        padding: 1rem;
    }

    .conversation-item {
        border: 1px solid #ccc;
        padding: 1rem;
        margin-bottom: 1rem;
        border-radius: 5px;
        background-color: white;
    }
</style>