"""
Local dictionary fallback for common words when APIs are unavailable
"""
from typing import Dict, Any, Optional
from loguru import logger

class LocalDictionary:
    """Local dictionary with common word definitions"""
    
    def __init__(self):
        # Common words with their definitions
        self.definitions = {
            "hello": {
                "word": "hello",
                "pronunciation": "/həˈloʊ/",
                "definitions": [
                    {
                        "part_of_speech": "interjection",
                        "definition": "Used as a greeting or to begin a phone conversation.",
                        "example": "Hello, how are you today?"
                    },
                    {
                        "part_of_speech": "noun",
                        "definition": "An expression of greeting.",
                        "example": "She gave me a friendly hello."
                    }
                ],
                "source": "Local Dictionary"
            },
            "world": {
                "word": "world",
                "pronunciation": "/wɜrld/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The earth, together with all of its countries, peoples, and natural features.",
                        "example": "The world is a beautiful place."
                    },
                    {
                        "part_of_speech": "noun",
                        "definition": "All of the people and societies on the earth.",
                        "example": "The whole world is watching."
                    }
                ],
                "source": "Local Dictionary"
            },
            "computer": {
                "word": "computer",
                "pronunciation": "/kəmˈpjuːtər/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "An electronic device for storing and processing data, typically in binary form.",
                        "example": "I use my computer for work and entertainment."
                    }
                ],
                "source": "Local Dictionary"
            },
            "technology": {
                "word": "technology",
                "pronunciation": "/tɛkˈnɒlədʒi/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The application of scientific knowledge for practical purposes.",
                        "example": "Modern technology has transformed our lives."
                    }
                ],
                "source": "Local Dictionary"
            },
            "programming": {
                "word": "programming",
                "pronunciation": "/ˈproʊɡræmɪŋ/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The process of writing computer programs.",
                        "example": "She studied programming in college."
                    }
                ],
                "source": "Local Dictionary"
            },
            "python": {
                "word": "python",
                "pronunciation": "/ˈpaɪθən/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "A high-level programming language known for its simplicity and readability.",
                        "example": "Python is popular for data science and web development."
                    },
                    {
                        "part_of_speech": "noun",
                        "definition": "A large nonvenomous snake that kills by constriction.",
                        "example": "The python coiled around its prey."
                    }
                ],
                "source": "Local Dictionary"
            },
            "artificial": {
                "word": "artificial",
                "pronunciation": "/ˌɑːtɪˈfɪʃəl/",
                "definitions": [
                    {
                        "part_of_speech": "adjective",
                        "definition": "Made or produced by human beings rather than occurring naturally.",
                        "example": "The flowers were artificial but looked very realistic."
                    }
                ],
                "source": "Local Dictionary"
            },
            "intelligence": {
                "word": "intelligence",
                "pronunciation": "/ɪnˈtɛlɪdʒəns/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The ability to acquire and apply knowledge and skills.",
                        "example": "Her intelligence was evident in her thoughtful responses."
                    }
                ],
                "source": "Local Dictionary"
            },
            "machine": {
                "word": "machine",
                "pronunciation": "/məˈʃiːn/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "An apparatus using mechanical power and having several parts.",
                        "example": "The factory uses machines to assemble products."
                    }
                ],
                "source": "Local Dictionary"
            },
            "learning": {
                "word": "learning",
                "pronunciation": "/ˈlɜːnɪŋ/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The acquisition of knowledge or skills through study or experience.",
                        "example": "Learning is a lifelong process."
                    }
                ],
                "source": "Local Dictionary"
            },
            "artificial intelligence": {
                "word": "artificial intelligence",
                "pronunciation": "/ˌɑːtɪˈfɪʃəl ɪnˈtelɪdʒəns/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The simulation of human intelligence in machines that are programmed to think and learn like humans.",
                        "example": "Artificial intelligence is transforming many industries."
                    }
                ],
                "source": "Local Dictionary"
            },
            "machine learning": {
                "word": "machine learning",
                "pronunciation": "/məˈʃiːn ˈlɜːnɪŋ/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "A subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.",
                        "example": "Machine learning algorithms can predict user behavior."
                    }
                ],
                "source": "Local Dictionary"
            },
            "deep learning": {
                "word": "deep learning",
                "pronunciation": "/diːp ˈlɜːnɪŋ/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "A subset of machine learning that uses neural networks with multiple layers to model and understand complex patterns.",
                        "example": "Deep learning is used in image recognition and natural language processing."
                    }
                ],
                "source": "Local Dictionary"
            },
            "data science": {
                "word": "data science",
                "pronunciation": "/ˈdeɪtə ˈsaɪəns/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "An interdisciplinary field that uses scientific methods, processes, algorithms, and systems to extract knowledge and insights from structured and unstructured data.",
                        "example": "Data science combines statistics, programming, and domain expertise."
                    }
                ],
                "source": "Local Dictionary"
            },
            "wisdom": {
                "word": "wisdom",
                "pronunciation": "/ˈwɪzdəm/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The quality of having experience, knowledge, and good judgment; the quality of being wise.",
                        "example": "With age comes wisdom and understanding."
                    }
                ],
                "source": "Local Dictionary"
            },
            "hypnotise": {
                "word": "hypnotise",
                "pronunciation": "/ˈhɪpnətaɪz/",
                "definitions": [
                    {
                        "part_of_speech": "verb",
                        "definition": "To put someone into a state of hypnosis, a trance-like state of focused attention and heightened suggestibility.",
                        "example": "The hypnotist was able to hypnotise the volunteer on stage."
                    }
                ],
                "source": "Local Dictionary"
            },
            "hypnotize": {
                "word": "hypnotize",
                "pronunciation": "/ˈhɪpnətaɪz/",
                "definitions": [
                    {
                        "part_of_speech": "verb",
                        "definition": "To put someone into a state of hypnosis, a trance-like state of focused attention and heightened suggestibility.",
                        "example": "The hypnotist was able to hypnotize the volunteer on stage."
                    }
                ],
                "source": "Local Dictionary"
            },
            "knowledge": {
                "word": "knowledge",
                "pronunciation": "/ˈnɒlɪdʒ/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "Facts, information, and skills acquired through experience or education; the theoretical or practical understanding of a subject.",
                        "example": "She has extensive knowledge of computer programming."
                    }
                ],
                "source": "Local Dictionary"
            },
            "education": {
                "word": "education",
                "pronunciation": "/ˌɛdʒʊˈkeɪʃən/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The process of receiving or giving systematic instruction, especially at a school or university.",
                        "example": "Education is the key to success in life."
                    }
                ],
                "source": "Local Dictionary"
            },
            "science": {
                "word": "science",
                "pronunciation": "/ˈsaɪəns/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The systematic study of the structure and behavior of the physical and natural world through observation and experiment.",
                        "example": "Modern science has made incredible discoveries."
                    }
                ],
                "source": "Local Dictionary"
            },
            "research": {
                "word": "research",
                "pronunciation": "/rɪˈsɜːtʃ/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The systematic investigation into and study of materials and sources in order to establish facts and reach new conclusions.",
                        "example": "The research team published their findings in a scientific journal."
                    }
                ],
                "source": "Local Dictionary"
            },
            "innovation": {
                "word": "innovation",
                "pronunciation": "/ˌɪnəˈveɪʃən/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "A new method, idea, product, etc., or the introduction of something new.",
                        "example": "The company is known for its innovation in renewable energy."
                    }
                ],
                "source": "Local Dictionary"
            },
            "creativity": {
                "word": "creativity",
                "pronunciation": "/ˌkriːeɪˈtɪvəti/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The use of imagination or original ideas to create something; inventiveness.",
                        "example": "Her creativity in solving problems is remarkable."
                    }
                ],
                "source": "Local Dictionary"
            },
            "vulnerable": {
                "word": "vulnerable",
                "pronunciation": "/ˈvʌlnərəbəl/",
                "definitions": [
                    {
                        "part_of_speech": "adjective",
                        "definition": "Susceptible to physical or emotional attack or harm; easily hurt or damaged.",
                        "example": "Children are particularly vulnerable to this disease."
                    }
                ],
                "source": "Local Dictionary"
            },
            "mentor": {
                "word": "mentor",
                "pronunciation": "/ˈmɛntɔː/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "An experienced and trusted adviser or guide who helps someone develop their skills and knowledge.",
                        "example": "She found a great mentor who helped her advance in her career."
                    }
                ],
                "source": "Local Dictionary"
            },
            "leadership": {
                "word": "leadership",
                "pronunciation": "/ˈliːdəʃɪp/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The action of leading a group of people or an organization; the ability to lead.",
                        "example": "His leadership skills helped the team achieve their goals."
                    }
                ],
                "source": "Local Dictionary"
            },
            "communication": {
                "word": "communication",
                "pronunciation": "/kəˌmjuːnɪˈkeɪʃən/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The imparting or exchanging of information by speaking, writing, or using some other medium.",
                        "example": "Effective communication is essential in any relationship."
                    }
                ],
                "source": "Local Dictionary"
            },
            "success": {
                "word": "success",
                "pronunciation": "/səkˈsɛs/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The accomplishment of an aim or purpose; the achievement of something desired or planned.",
                        "example": "The project was a great success due to teamwork."
                    }
                ],
                "source": "Local Dictionary"
            },
            "motivation": {
                "word": "motivation",
                "pronunciation": "/ˌmoʊtɪˈveɪʃən/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The reason or reasons one has for acting or behaving in a particular way; enthusiasm for doing something.",
                        "example": "Her motivation to help others drives her volunteer work."
                    }
                ],
                "source": "Local Dictionary"
            },
            "confidence": {
                "word": "confidence",
                "pronunciation": "/ˈkɒnfɪdəns/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "A feeling of self-assurance arising from one's appreciation of one's own abilities or qualities.",
                        "example": "She spoke with confidence during the presentation."
                    }
                ],
                "source": "Local Dictionary"
            },
            "experience": {
                "word": "experience",
                "pronunciation": "/ɪkˈspɪəriəns/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "Practical contact with and observation of facts or events; knowledge or skill acquired over time.",
                        "example": "His experience in the field made him an expert."
                    }
                ],
                "source": "Local Dictionary"
            },
            "development": {
                "word": "development",
                "pronunciation": "/dɪˈvɛləpmənt/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The process of developing or being developed; growth or advancement.",
                        "example": "The development of new technology has changed our lives."
                    }
                ],
                "source": "Local Dictionary"
            },
            "solution": {
                "word": "solution",
                "pronunciation": "/səˈluːʃən/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "A means of solving a problem or dealing with a difficult situation; the answer to a problem.",
                        "example": "We need to find a solution to this complex issue."
                    }
                ],
                "source": "Local Dictionary"
            },
            "strategy": {
                "word": "strategy",
                "pronunciation": "/ˈstrætədʒi/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "A plan of action designed to achieve a long-term or overall aim; a method or approach.",
                        "example": "The company developed a new marketing strategy."
                    }
                ],
                "source": "Local Dictionary"
            },
            "collaboration": {
                "word": "collaboration",
                "pronunciation": "/kəˌlæbəˈreɪʃən/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The action of working with someone to produce or create something; cooperation.",
                        "example": "The collaboration between the two teams led to great results."
                    }
                ],
                "source": "Local Dictionary"
            },
            "excellence": {
                "word": "excellence",
                "pronunciation": "/ˈɛksələns/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The quality of being outstanding or extremely good; superior merit or worth.",
                        "example": "The school is known for its academic excellence."
                    }
                ],
                "source": "Local Dictionary"
            },
            "potential": {
                "word": "potential",
                "pronunciation": "/pəˈtɛnʃəl/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The possibility of something happening or being developed; latent qualities or abilities.",
                        "example": "She has great potential as a leader."
                    }
                ],
                "source": "Local Dictionary"
            },
            "effortful": {
                "word": "effortful",
                "pronunciation": "/ˈɛfərtfəl/",
                "definitions": [
                    {
                        "part_of_speech": "adjective",
                        "definition": "Requiring or involving effort; not easy or automatic; demanding physical or mental exertion.",
                        "example": "Learning a new language is an effortful process that requires dedication and practice."
                    }
                ],
                "source": "Local Dictionary"
            },
            "dilatory": {
                "word": "dilatory",
                "pronunciation": "/ˈdɪləˌtɔri/",
                "definitions": [
                    {
                        "part_of_speech": "adjective",
                        "definition": "Tending to delay or procrastinate; slow to act; intended to cause delay.",
                        "example": "The dilatory tactics of the defense attorney prolonged the trial unnecessarily."
                    }
                ],
                "source": "Local Dictionary"
            },
            "colonel": {
                "word": "colonel",
                "pronunciation": "/ˈkɜrnəl/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "A military officer ranking above a lieutenant colonel and below a brigadier general; the highest field grade officer.",
                        "example": "Colonel Smith led the regiment into battle with great courage."
                    }
                ],
                "source": "Local Dictionary"
            },
            "serendipity": {
                "word": "serendipity",
                "pronunciation": "/ˌsɛrənˈdɪpəti/",
                "definitions": [
                    {
                        "part_of_speech": "noun",
                        "definition": "The occurrence and development of events by chance in a happy or beneficial way; a pleasant surprise.",
                        "example": "Finding that job was pure serendipity - I wasn't even looking for work at the time."
                    }
                ],
                "source": "Local Dictionary"
            },
            "arduous": {
                "word": "arduous",
                "pronunciation": "/ˈɑrdʒuəs/",
                "definitions": [
                    {
                        "part_of_speech": "adjective",
                        "definition": "Involving or requiring strenuous effort; difficult and tiring; requiring great exertion.",
                        "example": "The arduous climb to the mountain summit took all day and left us exhausted."
                    }
                ],
                "source": "Local Dictionary"
            },
            "encourage": {
                "word": "encourage",
                "pronunciation": "/ɪnˈkɜrɪdʒ/",
                "definitions": [
                    {
                        "part_of_speech": "verb",
                        "definition": "To give support, confidence, or hope to someone; to inspire with courage, spirit, or confidence.",
                        "example": "The coach encouraged the team to keep trying even when they were losing."
                    }
                ],
                "source": "Local Dictionary"
            }
        }
    
    def get_definition(self, word: str) -> Optional[Dict[str, Any]]:
        """Get definition for a word if available locally"""
        word_lower = word.lower().strip()
        
        if word_lower in self.definitions:
            logger.info(f"Found local definition for word: {word}")
            return self.definitions[word_lower]
        
        return None
    
    def has_word(self, word: str) -> bool:
        """Check if word is available in local dictionary"""
        return word.lower().strip() in self.definitions
    
    def get_available_words(self) -> list:
        """Get list of available words"""
        return list(self.definitions.keys())


# Global instance
local_dictionary = LocalDictionary() 