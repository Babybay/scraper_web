import React, { useState } from 'react';
import {
  View,
  TextInput,
  Text,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
  TouchableOpacity
} from 'react-native';
import axios from 'axios';

const API_BASE = 'http://192.168.1.8:5000'; // Ganti dengan IP server Anda

export default function App() {
  const [destination, setDestination] = useState('Jakarta');
  const [hotels, setHotels] = useState([]);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [chatMessage, setChatMessage] = useState('');
  const [chatResponse, setChatResponse] = useState('');

  const handleScrape = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/scrape`, {
        destination: destination || 'Jakarta'
      });

      if (response.data.success) {
        setHotels(response.data.hotels);
        Alert.alert('Success', `Found ${response.data.count} hotels in ${response.data.destination}`);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to scrape hotels');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    try {
      const response = await axios.post(`${API_BASE}/generate`);
      if (response.data.success) {
        setContent(response.data.content);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to generate content');
    }
  };

  const handlePublish = async () => {
    try {
      const response = await axios.post(`${API_BASE}/publish`);
      if (response.data.success) {
        Alert.alert('Success', 'Content published!');
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to publish content');
    }
  };

  const handleChat = async () => {
    if (!chatMessage.trim()) return;

    try {
      const response = await axios.post(`${API_BASE}/chatbot`, {
        message: chatMessage
      });

      if (response.data.success) {
        setChatResponse(response.data.response);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to get chatbot response');
    }
  };

  const getHotels = async () => {
    try {
      const response = await axios.get(`${API_BASE}/hotels`);
      setHotels(response.data.hotels);
    } catch (error) {
      Alert.alert('Error', 'Failed to get hotels');
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>🏨 Hotel Scraper Dashboard</Text>
        <Text style={styles.subtitle}>Automated Hotel Data & Social Media</Text>
      </View>

      {/* Scraping Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Scrape Hotels</Text>
        <TextInput
          style={styles.input}
          placeholder="Destination (e.g., Jakarta, Bali)"
          value={destination}
          onChangeText={setDestination}
        />
        <TouchableOpacity style={styles.button} onPress={handleScrape} disabled={loading}>
          <Text style={styles.buttonText}>
            {loading ? 'Scraping...' : '🔍 Scrape Hotels'}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.secondaryButton} onPress={getHotels}>
          <Text style={styles.secondaryButtonText}>📋 Get Current Hotels</Text>
        </TouchableOpacity>
      </View>

      {/* Hotels List */}
      {hotels.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Hotels Found ({hotels.length})</Text>
          {hotels.slice(0, 5).map((hotel, index) => (
            <View key={index} style={styles.hotelCard}>
              <Text style={styles.hotelName}>{hotel.name}</Text>
              {hotel.price && <Text style={styles.hotelPrice}>💰 {hotel.price}</Text>}
              {hotel.rating && <Text style={styles.hotelRating}>⭐ {hotel.rating}</Text>}
            </View>
          ))}
        </View>
      )}

      {/* Content Generation */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Content Generation</Text>
        <TouchableOpacity style={styles.button} onPress={handleGenerate}>
          <Text style={styles.buttonText}>✨ Generate Social Media Post</Text>
        </TouchableOpacity>

        {content ? (
          <View style={styles.contentBox}>
            <Text style={styles.contentText}>{content}</Text>
          </View>
        ) : null}

        <TouchableOpacity style={styles.publishButton} onPress={handlePublish}>
          <Text style={styles.publishButtonText}>🚀 Publish to Social Media</Text>
        </TouchableOpacity>
      </View>

      {/* Chatbot */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Travel Assistant Chat</Text>
        <TextInput
          style={styles.input}
          placeholder="Ask about hotels or travel..."
          value={chatMessage}
          onChangeText={setChatMessage}
        />
        <TouchableOpacity style={styles.button} onPress={handleChat}>
          <Text style={styles.buttonText}>💬 Ask Assistant</Text>
        </TouchableOpacity>

        {chatResponse ? (
          <View style={styles.chatResponse}>
            <Text style={styles.chatResponseText}>{chatResponse}</Text>
          </View>
        ) : null}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: 'white',
    padding: 20,
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  section: {
    backgroundColor: 'white',
    margin: 10,
    padding: 15,
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#333',
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
    fontSize: 16,
  },
  button: {
    backgroundColor: '#4F46E5',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 10,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    backgroundColor: '#6B7280',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  secondaryButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '500',
  },
  publishButton: {
    backgroundColor: '#10B981',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 10,
  },
  publishButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  hotelCard: {
    backgroundColor: '#f8f9fa',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#4F46E5',
  },
  hotelName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  hotelPrice: {
    color: '#059669',
    fontSize: 14,
  },
  hotelRating: {
    color: '#D97706',
    fontSize: 14,
  },
  contentBox: {
    backgroundColor: '#f0f9ff',
    padding: 12,
    borderRadius: 8,
    marginTop: 10,
    borderLeftWidth: 3,
    borderLeftColor: '#0EA5E9',
  },
  contentText: {
    fontSize: 14,
    lineHeight: 20,
    color: '#333',
  },
  chatResponse: {
    backgroundColor: '#f0fdf4',
    padding: 12,
    borderRadius: 8,
    marginTop: 10,
    borderLeftWidth: 3,
    borderLeftColor: '#10B981',
  },
  chatResponseText: {
    fontSize: 14,
    lineHeight: 20,
    color: '#333',
  },
});