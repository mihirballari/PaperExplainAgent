window.HELP_IMPROVE_VIDEOJS = false;

// More Works Dropdown Functionality
function toggleMoreWorks() {
    const dropdown = document.getElementById('moreWorksDropdown');
    const button = document.querySelector('.more-works-btn');
    
    if (dropdown.classList.contains('show')) {
        dropdown.classList.remove('show');
        button.classList.remove('active');
    } else {
        dropdown.classList.add('show');
        button.classList.add('active');
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const container = document.querySelector('.more-works-container');
    const dropdown = document.getElementById('moreWorksDropdown');
    const button = document.querySelector('.more-works-btn');
    
    if (container && !container.contains(event.target)) {
        dropdown.classList.remove('show');
        button.classList.remove('active');
    }
});

// Close dropdown on escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const dropdown = document.getElementById('moreWorksDropdown');
        const button = document.querySelector('.more-works-btn');
        dropdown.classList.remove('show');
        button.classList.remove('active');
    }
});

// Copy BibTeX to clipboard
function copyBibTeX() {
    const bibtexElement = document.getElementById('bibtex-code');
    const button = document.querySelector('.copy-bibtex-btn');
    const copyText = button.querySelector('.copy-text');
    
    if (bibtexElement) {
        navigator.clipboard.writeText(bibtexElement.textContent).then(function() {
            // Success feedback
            button.classList.add('copied');
            copyText.textContent = 'Cop';
            
            setTimeout(function() {
                button.classList.remove('copied');
                copyText.textContent = 'Copy';
            }, 2000);
        }).catch(function(err) {
            console.error('Failed to copy: ', err);
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = bibtexElement.textContent;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            
            button.classList.add('copied');
            copyText.textContent = 'Cop';
            setTimeout(function() {
                button.classList.remove('copied');
                copyText.textContent = 'Copy';
            }, 2000);
        });
    }
}

// Scroll to top functionality
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// Show/hide scroll to top button
window.addEventListener('scroll', function() {
    const scrollButton = document.querySelector('.scroll-to-top');
    if (window.pageYOffset > 300) {
        scrollButton.classList.add('visible');
    } else {
        scrollButton.classList.remove('visible');
    }
});

// Video carousel autoplay when in view
function setupVideoCarouselAutoplay() {
    const carouselVideos = document.querySelectorAll('.results-carousel video');
    
    if (carouselVideos.length === 0) return;
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            const video = entry.target;
            if (entry.isIntersecting) {
                // Video is in view, play it
                video.play().catch(e => {
                    // Autoplay failed, probably due to browser policy
                    console.log('Autoplay prevented:', e);
                });
            } else {
                // Video is out of view, pause it
                video.pause();
            }
        });
    }, {
        threshold: 0.5 // Trigger when 50% of the video is visible
    });
    
    carouselVideos.forEach(video => {
        observer.observe(video);
    });
}

// Render public comments into the list container
function renderPublicComments(listEl, comments) {
    if (!listEl) return;

    if (!comments || comments.length === 0) {
        listEl.innerHTML = '<div class="comment-empty">No public comments yet. Be the first to share your thoughts.</div>';
        return;
    }

    const fragment = document.createDocumentFragment();

    comments.forEach(comment => {
        const item = document.createElement('div');
        item.className = 'comment-item';

        const meta = document.createElement('div');
        meta.className = 'comment-meta';

        const name = document.createElement('span');
        name.textContent = comment.name || 'Anonymous';

        const time = document.createElement('span');
        const date = comment.timestamp ? new Date(comment.timestamp) : new Date();
        time.textContent = date.toLocaleString();

        meta.appendChild(name);
        meta.appendChild(time);

        const body = document.createElement('div');
        body.className = 'comment-body';
        body.textContent = comment.message || '';

        item.appendChild(meta);
        item.appendChild(body);
        fragment.appendChild(item);
    });

    listEl.innerHTML = '';
    listEl.appendChild(fragment);
}

// Handle comment submission and storage/email
function setupCommentsSection() {
    const form = document.getElementById('commentForm');
    const list = document.getElementById('publicComments');
    const status = document.getElementById('commentStatus');

    if (!form || !list || !status) return;

    const storageKey = 'paperExplainPublicComments';
    const mailRecipient = form.dataset.mailTo || 'your-email@example.com';

    let comments = [];
    try {
        const stored = localStorage.getItem(storageKey);
        comments = stored ? JSON.parse(stored) : [];
    } catch (e) {
        comments = [];
    }

    renderPublicComments(list, comments);

    form.addEventListener('submit', function(event) {
        event.preventDefault();

        const formData = new FormData(form);
        const name = (formData.get('name') || '').trim();
        const email = (formData.get('email') || '').trim();
        const message = (formData.get('comment') || '').trim();
        const mode = form.querySelector('input[name="commentMode"]:checked')?.value || 'public';

        status.classList.remove('is-hidden', 'has-text-danger', 'has-text-success');

        if (!message) {
            status.classList.add('has-text-danger');
            status.textContent = 'Please add a comment before submitting.';
            return;
        }

        if (mode === 'email') {
            const subject = encodeURIComponent('PaperExplainAgent feedback');
            const body = encodeURIComponent(
                `Name: ${name || 'Anonymous'}\nEmail: ${email || 'Not provided'}\n\n${message}`
            );
            window.location.href = `mailto:${mailRecipient}?subject=${subject}&body=${body}`;
            status.classList.add('has-text-success');
            status.textContent = 'Opening your email app...';
            return;
        }

        const entry = {
            name: name || 'Anonymous',
            email: email || '',
            message,
            timestamp: new Date().toISOString()
        };

        comments = [entry, ...comments].slice(0, 25); // keep it lightweight
        localStorage.setItem(storageKey, JSON.stringify(comments));
        renderPublicComments(list, comments);

        form.reset();
        form.querySelector('input[name="commentMode"][value="public"]').checked = true;
        status.classList.add('has-text-success');
        status.textContent = 'Your comment was added locally.';
    });
}

$(document).ready(function() {
    // Check for click events on the navbar burger icon

    var options = {
		slidesToScroll: 1,
		slidesToShow: 1,
		loop: true,
		infinite: true,
		autoplay: true,
		autoplaySpeed: 5000,
    }

    // Initialize all div with carousel class
    var carousels = bulmaCarousel.attach('.carousel', options);
	
    bulmaSlider.attach();
    
    // Setup video autoplay for carousel
    setupVideoCarouselAutoplay();

    // Setup comments
    setupCommentsSection();

})
